"""Supabase database client."""
from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from .config import settings
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

# Zona horaria de Perú
PERU_TZ = ZoneInfo("America/Lima")


class SupabaseClient:
    """Wrapper for Supabase operations."""
    
    _client: Optional[Client] = None
    _is_connected: bool = False
    
    @property
    def client(self) -> Optional[Client]:
        if self._client is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                logger.warning("SUPABASE_URL y SUPABASE_KEY no configuradas - modo sin DB")
                return None
            try:
                self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                self._is_connected = True
            except Exception as e:
                logger.error(f"Error conectando a Supabase: {e}")
                self._is_connected = False
                return None
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Verificar si hay conexión a Supabase."""
        if self._client is None:
            _ = self.client  # Intenta conectar
        return self._is_connected
    
    # =========================================================================
    # Métodos para obtener snapshots de posiciones regionales
    # =========================================================================
    
    async def get_latest_region_snapshot(self, region_code: str = "NACIONAL") -> Optional[Dict]:
        """
        Get the latest position snapshot for a region, formatted for /results/live/{region}.
        
        Returns the snapshot in a format compatible with the live results endpoint:
        - candidates list with top 3 candidates
        - totals with vote summaries
        - rivalry info for the 2nd/3rd place race
        """
        snapshot = await self.get_latest_position_snapshot(region_code=region_code)
        
        if not snapshot:
            return None
        
        # Build candidates list - ONLY rivalry parties (pos2 and pos3)
        # We intentionally exclude pos1 (Fujimori) - this API is for tracking the 
        # rivalry between JUNTOS POR EL PERÚ (ID 10) and RENOVACIÓN POPULAR (ID 35)
        candidates = []
        
        # 2nd place - JUNTOS POR EL PERÚ (party_id "10")
        candidates.append({
            "id": snapshot.get("pos2_candidate_id"),
            "name": snapshot.get("pos2_candidate_name"),
            "party_name": snapshot.get("pos2_party_name"),
            "party_id": snapshot.get("pos2_party_id"),
            "votes": snapshot.get("pos2_votes", 0),
            "percentage": snapshot.get("pos2_percentage", 0),
            "percentage_emitted": snapshot.get("pos2_percentage_emitted"),
        })
        
        # 3rd place - RENOVACIÓN POPULAR (party_id "35")
        candidates.append({
            "id": snapshot.get("pos3_candidate_id"),
            "name": snapshot.get("pos3_candidate_name"),
            "party_name": snapshot.get("pos3_party_name"),
            "party_id": snapshot.get("pos3_party_id"),
            "votes": snapshot.get("pos3_votes", 0),
            "percentage": snapshot.get("pos3_percentage", 0),
            "percentage_emitted": snapshot.get("pos3_percentage_emitted"),
        })
        
        # Build rivalry info
        pos2_votes = snapshot.get("pos2_votes", 0)
        pos3_votes = snapshot.get("pos3_votes", 0)
        pos2_pct = snapshot.get("pos2_percentage", 0)
        pos3_pct = snapshot.get("pos3_percentage", 0)
        
        rivalry = {
            "leader": "POS2" if pos2_votes > pos3_votes else ("POS3" if pos3_votes > pos2_votes else "TIE"),
            "gap": abs(pos2_votes - pos3_votes),
            "gap_percent": round(abs(pos2_pct - pos3_pct), 2),
            "pos2_party_id": snapshot.get("pos2_party_id"),
            "pos3_party_id": snapshot.get("pos3_party_id"),
        }
        
        from .services.scraper import REGIONS
        region_info = REGIONS.get(region_code, {})
        
        return {
            "election_type": "PRESI",
            "region_code": region_code,
            "region_name": region_info.get("name", region_code),
            "timestamp": snapshot.get("timestamp"),
            "candidates": candidates,
            "totals": {
                "valid_votes": snapshot.get("total_valid_votes"),
                "blank_votes": snapshot.get("blank_votes"),
                "null_votes": snapshot.get("null_votes"),
                "emitted_votes": snapshot.get("total_emitted_votes"),
            },
            "rivalry": rivalry,
            "all_candidates_count": 2,  # Rivalry parties only: JUNTOS + RENOVACIÓN
            "source": "database",
            "snapshot_id": snapshot.get("id"),
        }
    
    # =========================================================================
    # Métodos para position_snapshots (2do y 3er puesto)
    # =========================================================================
    
    async def has_votes_changed(self, new_data: Dict[str, Any], region_code: str = "NACIONAL") -> bool:
        """
        Verificar si los votos o actas han cambiado respecto al último snapshot de la región.
        Compara votos (enteros) y actas_percentage con precisión exacta.
        
        Args:
            new_data: Datos del nuevo snapshot
            region_code: Código de región (default: NACIONAL)
        
        Returns:
            True si hay CUALQUIER cambio en votos de pos2, pos3, o actas_percentage.
            Uses 6-decimal rounding to avoid float noise, but captures all real changes.
        """
        latest = await self.get_latest_position_snapshot(region_code=region_code)
        
        if not latest:
            # No hay snapshot previo para esta región, siempre insertar
            logger.info(f"No hay snapshot previo para {region_code} - insertando primer registro")
            return True
        
        # Comparar votos del 2do puesto
        old_pos2_votes = latest.get("pos2_votes", 0)
        new_pos2_votes = new_data["pos2"]["votes"]
        
        # Comparar votos del 3er puesto
        old_pos3_votes = latest.get("pos3_votes", 0)
        new_pos3_votes = new_data["pos3"]["votes"]
        
        # Comparar actas_percentage - EXACT comparison (round to 6 decimals to avoid float noise)
        # This captures ALL changes from ONPE, no matter how small
        old_actas_pct = latest.get("actas_percentage", 0) or 0
        new_actas_pct = new_data.get("actas_percentage", 0) or 0
        # Round to 6 decimals to eliminate float precision noise, then compare directly
        old_actas_rounded = round(old_actas_pct, 6)
        new_actas_rounded = round(new_actas_pct, 6)
        actas_changed = new_actas_rounded != old_actas_rounded
        
        pos2_changed = old_pos2_votes != new_pos2_votes
        pos3_changed = old_pos3_votes != new_pos3_votes
        
        if pos2_changed or pos3_changed or actas_changed:
            logger.info(
                f"Cambio detectado [{region_code}] - Pos2: {old_pos2_votes} -> {new_pos2_votes}, "
                f"Pos3: {old_pos3_votes} -> {new_pos3_votes}, "
                f"Actas: {old_actas_pct}% -> {new_actas_pct}%"
            )
            return True
        else:
            logger.debug(
                f"Sin cambios [{region_code}] - Pos2: {new_pos2_votes} votos, Pos3: {new_pos3_votes} votos, "
                f"Actas: {new_actas_pct}%"
            )
            return False

    async def insert_position_snapshot(self, data: Dict[str, Any], region_code: str = "NACIONAL") -> Optional[Dict]:
        """
        Insertar snapshot de posiciones 2 y 3 para una región específica.
        El trigger en la DB calculará automáticamente los cambios.
        
        Args:
            data: Datos del snapshot
            region_code: Código de región (default: NACIONAL)
        """
        if not self.client:
            logger.warning("No hay conexión a Supabase - snapshot no guardado")
            return None
        try:
            response = self.client.table("position_snapshots").insert({
                "region_code": region_code,
                "timestamp": data.get("timestamp", datetime.now(PERU_TZ).isoformat()),
                
                # 2do puesto
                "pos2_candidate_id": data["pos2"]["candidate_id"],
                "pos2_candidate_name": data["pos2"]["candidate_name"],
                "pos2_party_name": data["pos2"]["party_name"],
                "pos2_party_id": data["pos2"].get("party_id"),
                "pos2_votes": data["pos2"]["votes"],
                "pos2_percentage": data["pos2"]["percentage"],
                "pos2_percentage_emitted": data["pos2"].get("percentage_emitted"),
                
                # 3er puesto
                "pos3_candidate_id": data["pos3"]["candidate_id"],
                "pos3_candidate_name": data["pos3"]["candidate_name"],
                "pos3_party_name": data["pos3"]["party_name"],
                "pos3_party_id": data["pos3"].get("party_id"),
                "pos3_votes": data["pos3"]["votes"],
                "pos3_percentage": data["pos3"]["percentage"],
                "pos3_percentage_emitted": data["pos3"].get("percentage_emitted"),
                
                # Totales
                "total_valid_votes": data.get("total_valid_votes"),
                "total_emitted_votes": data.get("total_emitted_votes"),
                "blank_votes": data.get("blank_votes"),
                "null_votes": data.get("null_votes"),
                
                # 1er puesto (referencia)
                "pos1_candidate_name": data.get("pos1_name"),
                "pos1_votes": data.get("pos1_votes"),
                "pos1_percentage": data.get("pos1_percentage"),
                
                # Actas progress
                "actas_percentage": data.get("actas_percentage", 0),
                "actas_counted": data.get("actas_counted", 0),
                "actas_total": data.get("actas_total", 0),
            }).execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error inserting position snapshot: {e}")
            raise
    
    async def get_latest_position_snapshot(self, region_code: str = "NACIONAL") -> Optional[Dict]:
        """
        Obtener el último snapshot de posiciones para una región.
        
        Args:
            region_code: Código de región (default: NACIONAL)
        """
        if not self.client:
            return None
        try:
            response = self.client.table("position_snapshots").select(
                "*"
            ).eq(
                "region_code", region_code
            ).order(
                "timestamp", desc=True
            ).limit(1).execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.warning(f"Error fetching latest position snapshot for {region_code}: {e}")
            return None
    
    async def get_position_history(self, hours: int = 24, limit: int = 100, region_code: Optional[str] = None) -> List[Dict]:
        """
        Obtener historial de snapshots de posiciones.
        
        Args:
            hours: Horas de historial a obtener
            limit: Máximo número de resultados
            region_code: Código de región (si no se especifica, retorna todas las regiones)
        """
        if not self.client:
            return []
        try:
            from datetime import timedelta
            cutoff = datetime.now(PERU_TZ) - timedelta(hours=hours)
            
            query = self.client.table("position_snapshots").select(
                "*"
            ).gte(
                "timestamp", cutoff.isoformat()
            )
            
            # Filtrar por región si se especifica
            if region_code:
                query = query.eq("region_code", region_code)
            
            response = query.order(
                "timestamp", desc=True
            ).limit(limit).execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.warning(f"Error fetching position history: {e}")
            return []
    
    async def get_all_position_snapshots_for_projection(self, region_code: str = "TOTAL") -> List[Dict]:
        """
        Obtener TODOS los snapshots de una región para calcular proyección.
        Ordenados por timestamp DESC (más reciente primero).
        NO tiene límite de tiempo — usa todos los snapshots disponibles.
        """
        if not self.client:
            return []
        try:
            query = self.client.table("position_snapshots").select(
                "timestamp, pos2_votes, pos3_votes, actas_percentage, "
                "pos2_candidate_id, pos3_candidate_id, pos2_party_name, pos3_party_name"
            ).eq("region_code", region_code).order(
                "timestamp", desc=True
            ).execute()
            
            return query.data if query.data else []
        except Exception as e:
            logger.warning(f"Error fetching all snapshots for projection: {e}")
            return []
    
    async def get_position_changes(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Obtener historial de cambios entre snapshots."""
        if not self.client:
            return []
        try:
            from datetime import timedelta
            cutoff = datetime.now(PERU_TZ) - timedelta(hours=hours)
            
            response = self.client.table("position_changes").select(
                "*"
            ).gte(
                "timestamp", cutoff.isoformat()
            ).order(
                "timestamp", desc=True
            ).limit(limit).execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.warning(f"Error fetching position changes: {e}")
            return []
    
    async def get_race_status(self) -> Optional[Dict]:
        """Obtener estado actual de la carrera (vista current_race_status)."""
        if not self.client:
            return None
        try:
            response = self.client.table("current_race_status").select(
                "*"
            ).limit(1).execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.warning(f"Error fetching race status: {e}")
            return None
    
    async def should_take_snapshot(self, interval_minutes: int = 15) -> bool:
        """Verificar si ya pasaron N minutos desde el último snapshot."""
        if not self.client:
            return False  # Sin DB, no podemos guardar snapshots
        try:
            latest = await self.get_latest_position_snapshot()
            
            if not latest:
                return True  # No hay snapshots, tomar el primero
            
            last_timestamp = datetime.fromisoformat(
                latest["timestamp"].replace("Z", "+00:00")
            )
            now = datetime.now(last_timestamp.tzinfo)
            
            minutes_elapsed = (now - last_timestamp).total_seconds() / 60
            return minutes_elapsed >= interval_minutes
        except Exception as e:
            print(f"Error checking snapshot interval: {e}")
            return True  # En caso de error, permitir snapshot

    async def get_actas_progress(self, region_code: str = "NACIONAL") -> Optional[Dict]:
        """
        Get actas progress from database.
        Reads from position_snapshots table which stores actas data during scraping.
        
        Args:
            region_code: Region code
        
        Returns:
            Dict with actas progress data or None
        """
        # Get the latest position snapshot which contains actas data
        snapshot = await self.get_latest_position_snapshot(region_code)
        
        if not snapshot:
            return None
        
        # Import REGIONS here to avoid circular import
        from .services.scraper import REGIONS
        region_info = REGIONS.get(region_code, {})
        
        # Build actas response from snapshot data
        return {
            "region_code": region_code,
            "region_name": region_info.get("name", region_code),
            "actas_percentage": snapshot.get("actas_percentage", 0) or 0,
            "actas_counted": snapshot.get("actas_counted", 0) or 0,
            "actas_total": snapshot.get("actas_total", 0) or 0,
            "total_emitted_votes": snapshot.get("total_emitted_votes", 0) or 0,
            "total_valid_votes": snapshot.get("total_valid_votes", 0) or 0,
            "timestamp": snapshot.get("timestamp"),
            "source": "database",
        }

    # =========================================================================
    # Métodos para notificaciones de cambios
    # =========================================================================

    async def insert_change_notification(
        self,
        region_code: str,
        region_name: str,
        juntos_votes: int,
        juntos_change: int,
        renovacion_votes: int,
        renovacion_change: int,
        actas_percentage: float = 0
    ) -> Optional[Dict]:
        """
        Insertar una notificación de cambio para una región.
        Solo para departamentos y EXTRANJERO, NO para TOTAL/PERU.
        
        Args:
            region_code: Código de la región
            region_name: Nombre de la región
            juntos_votes: Votos actuales de JUNTOS
            juntos_change: Cambio en votos de JUNTOS
            renovacion_votes: Votos actuales de RENOVACIÓN
            renovacion_change: Cambio en votos de RENOVACIÓN
            actas_percentage: Porcentaje de actas procesadas
        
        Returns:
            Dict con la notificación insertada o None
        """
        if not self.client:
            logger.warning("No hay conexión a Supabase - notificación no guardada")
            return None
        
        # Calcular quién lidera
        leader = "POS2" if juntos_votes > renovacion_votes else ("POS3" if renovacion_votes > juntos_votes else "TIE")
        
        # Calcular brecha y cambio
        gap = abs(juntos_votes - renovacion_votes)
        gap_change = juntos_change - renovacion_change  # Positivo = JUNTOS ganó terreno
        
        # Determinar tipo de notificación
        notification_type = "vote_change"
        
        # Generar mensaje legible
        message = self._generate_notification_message(
            region_name=region_name,
            leader=leader,
            juntos_votes=juntos_votes,
            juntos_change=juntos_change,
            renovacion_votes=renovacion_votes,
            renovacion_change=renovacion_change,
            gap=gap,
            gap_change=gap_change,
            actas_percentage=actas_percentage
        )
        
        try:
            # Use Peru timezone for timestamp
            peru_timestamp = datetime.now(PERU_TZ).isoformat()
            
            response = self.client.table("change_notifications").insert({
                "region_code": region_code,
                "region_name": region_name,
                "timestamp": peru_timestamp,  # Explicit Peru time
                "notification_type": notification_type,
                "leader": leader,
                "juntos_votes": juntos_votes,
                "juntos_change": juntos_change,
                "renovacion_votes": renovacion_votes,
                "renovacion_change": renovacion_change,
                "gap": gap,
                "gap_change": gap_change,
                "actas_percentage": actas_percentage,
                "message": message,
            }).execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error inserting change notification: {e}")
            return None
    
    def _generate_notification_message(
        self,
        region_name: str,
        leader: str,
        juntos_votes: int,
        juntos_change: int,
        renovacion_votes: int,
        renovacion_change: int,
        gap: int,
        gap_change: int,
        actas_percentage: float
    ) -> str:
        """Genera un mensaje legible para la notificación."""
        # Determinar quién lidera
        if leader == "POS2":
            leader_name = "JUNTOS"
            leader_emoji = "🔴"
        elif leader == "POS3":
            leader_name = "RENOVACIÓN"
            leader_emoji = "🔵"
        else:
            leader_name = "EMPATE"
            leader_emoji = "⚖️"
        
        # Generar partes del mensaje
        parts = []
        
        # Quién ganó votos
        if juntos_change > 0 and renovacion_change > 0:
            if juntos_change > renovacion_change:
                parts.append(f"🔴 +{juntos_change:,} vs 🔵 +{renovacion_change:,}")
            elif renovacion_change > juntos_change:
                parts.append(f"🔵 +{renovacion_change:,} vs 🔴 +{juntos_change:,}")
            else:
                parts.append(f"Ambos +{juntos_change:,} votos")
        elif juntos_change > 0:
            parts.append(f"🔴 JUNTOS +{juntos_change:,}")
        elif renovacion_change > 0:
            parts.append(f"🔵 RENOVACIÓN +{renovacion_change:,}")
        
        # Brecha actual
        if gap > 0:
            parts.append(f"Brecha: {gap:,} votos ({leader_emoji} {leader_name})")
        
        return " | ".join(parts) if parts else f"Actualización en {region_name}"
    
    async def get_notifications(
        self,
        limit: int = 50,
        hours: int = 24,
    ) -> List[Dict]:
        """
        Obtener notificaciones de cambios.
        
        SIMPLIFIED: No hay tracking de "leído" porque las notificaciones
        son COMPARTIDAS entre todos los usuarios.
        Cache is handled at endpoint level via fastapi-cache2.
        
        Args:
            limit: Máximo número de notificaciones
            hours: Horas hacia atrás
        
        Returns:
            Lista de notificaciones
        """
        if not self.client:
            return []
        
        try:
            from datetime import timedelta
            cutoff = datetime.now(PERU_TZ) - timedelta(hours=hours)
            
            response = self.client.table("change_notifications").select(
                "*"
            ).gte(
                "timestamp", cutoff.isoformat()
            ).order(
                "timestamp", desc=True
            ).limit(limit).execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.warning(f"Error fetching notifications: {e}")
            return []


# Global instance
db = SupabaseClient()
