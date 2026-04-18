"""ONPE data scraper service - Uses official JSON API."""
import asyncio
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any, List
import logging
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Rivalry tracking: Only these two parties matter for regional analysis
RIVALRY_PARTIES = {
    "10": "JUNTOS POR EL PERÚ",
    "35": "RENOVACIÓN POPULAR"
}
JUNTOS_PARTY_ID = "10"
RENOVACION_PARTY_ID = "35"

# Zona horaria de Perú
PERU_TZ = ZoneInfo("America/Lima")

# ONPE Official API base endpoint
ONPE_API_BASE = (
    "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/"
    "eleccion-presidencial/participantes-ubicacion-geografica-nombre"
)

# ONPE Actas progress endpoint
ONPE_ACTAS_BASE = (
    "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/"
    "resumen-general/totales"
)

# ONPE Official API endpoint - votos totales nacionales
ONPE_API_URL = f"{ONPE_API_BASE}?idEleccion=10&tipoFiltro=eleccion"

# Base URL for images
ONPE_BASE_URL = "https://resultadoelectoral.onpe.gob.pe"

# Region cache: 30 entries max, 30 second TTL
region_cache: TTLCache = TTLCache(maxsize=30, ttl=30)

# Semaphore to limit concurrent ONPE requests (max 2)
onpe_semaphore = asyncio.Semaphore(2)

# =============================================================================
# REGION DEFINITIONS - 4 CATEGORIES:
# 1. TOTAL: Todo (Perú + Extranjero) - tipoFiltro=eleccion
# 2. PERU: Solo territorio nacional - tipoFiltro=ambito_geografico, idAmbitoGeografico=1
# 3. EXTRANJERO: Solo peruanos afuera - tipoFiltro=ambito_geografico, idAmbitoGeografico=2
# 4. Departamentos: Regiones individuales - tipoFiltro=ubigeo_nivel_01
# =============================================================================

REGIONS: Dict[str, Dict[str, Any]] = {
    # === CATEGORÍA 1: TOTAL (Perú + Extranjero) ===
    "TOTAL": {
        "name": "Total (Perú + Extranjero)",
        "category": "total",
        "ubigeo": None,
        "params": {
            "tipoFiltro": "eleccion",
            "idEleccion": "10"
        },
        "actas_params": {
            "idEleccion": "10",
            "tipoFiltro": "eleccion"
        }
    },
    
    # === CATEGORÍA 2: PERU (Solo territorio nacional) ===
    "PERU": {
        "name": "Perú (Solo Nacional)",
        "category": "peru",
        "ubigeo": None,
        "params": {
            "tipoFiltro": "ambito_geografico",
            "idAmbitoGeografico": "1",
            "idEleccion": "10"
        },
        "actas_params": {
            "idAmbitoGeografico": "1",
            "idEleccion": "10",
            "tipoFiltro": "ambito_geografico"
        }
    },
    
    # === CATEGORÍA 3: EXTRANJERO (Peruanos en el exterior) ===
    "EXTRANJERO": {
        "name": "Extranjero",
        "category": "extranjero",
        "ubigeo": None,
        "params": {
            "tipoFiltro": "ambito_geografico",
            "idAmbitoGeografico": "2",
            "idEleccion": "10"
        },
        "actas_params": {
            "idAmbitoGeografico": "2",
            "idEleccion": "10",
            "tipoFiltro": "ambito_geografico"
        }
    },
    
    # === CATEGORÍA 4: DEPARTAMENTOS (Regiones individuales dentro de Perú) ===
    "010000": {"name": "Amazonas", "category": "departamento", "ubigeo": "010000"},
    "020000": {"name": "Áncash", "category": "departamento", "ubigeo": "020000"},
    "030000": {"name": "Apurímac", "category": "departamento", "ubigeo": "030000"},
    "040000": {"name": "Arequipa", "category": "departamento", "ubigeo": "040000"},
    "050000": {"name": "Ayacucho", "category": "departamento", "ubigeo": "050000"},
    "060000": {"name": "Cajamarca", "category": "departamento", "ubigeo": "060000"},
    "070000": {"name": "Cusco", "category": "departamento", "ubigeo": "070000"},
    "080000": {"name": "Huancavelica", "category": "departamento", "ubigeo": "080000"},
    "090000": {"name": "Huánuco", "category": "departamento", "ubigeo": "090000"},
    "100000": {"name": "Ica", "category": "departamento", "ubigeo": "100000"},
    "110000": {"name": "Junín", "category": "departamento", "ubigeo": "110000"},
    "120000": {"name": "La Libertad", "category": "departamento", "ubigeo": "120000"},
    "130000": {"name": "Lambayeque", "category": "departamento", "ubigeo": "130000"},
    "140000": {"name": "Lima", "category": "departamento", "ubigeo": "140000"},
    "150000": {"name": "Loreto", "category": "departamento", "ubigeo": "150000"},
    "160000": {"name": "Madre de Dios", "category": "departamento", "ubigeo": "160000"},
    "170000": {"name": "Moquegua", "category": "departamento", "ubigeo": "170000"},
    "180000": {"name": "Pasco", "category": "departamento", "ubigeo": "180000"},
    "190000": {"name": "Piura", "category": "departamento", "ubigeo": "190000"},
    "200000": {"name": "Puno", "category": "departamento", "ubigeo": "200000"},
    "210000": {"name": "San Martín", "category": "departamento", "ubigeo": "210000"},
    "220000": {"name": "Tacna", "category": "departamento", "ubigeo": "220000"},
    "230000": {"name": "Tumbes", "category": "departamento", "ubigeo": "230000"},
    "240000": {"name": "Callao", "category": "departamento", "ubigeo": "240000"},
    "250000": {"name": "Ucayali", "category": "departamento", "ubigeo": "250000"},
}

# Backwards compatibility: NACIONAL = TOTAL
REGIONS["NACIONAL"] = REGIONS["TOTAL"]


def get_region_params(region_code: str) -> Optional[Dict[str, str]]:
    """Build ONPE API parameters for a region."""
    region = REGIONS.get(region_code)
    if not region:
        return None
    
    # Special cases with custom params (TOTAL, PERU, EXTRANJERO)
    if "params" in region:
        return region["params"]
    
    # Standard departments use ubigeo_nivel_01
    return {
        "tipoFiltro": "ubigeo_nivel_01",
        "idAmbitoGeografico": "1",
        "ubigeoNivel1": region["ubigeo"],
        "idEleccion": "10"
    }


def get_actas_params(region_code: str) -> Optional[Dict[str, str]]:
    """Build ONPE actas API parameters for a region."""
    region = REGIONS.get(region_code)
    if not region:
        return None
    
    # Special cases with custom actas_params (TOTAL, PERU, EXTRANJERO)
    if "actas_params" in region:
        return region["actas_params"]
    
    # Departments (ubigeo_nivel_01)
    if region.get("ubigeo"):
        return {
            "idAmbitoGeografico": "1",
            "idEleccion": "10",
            "tipoFiltro": "ubigeo_nivel_01",
            "idUbigeoDepartamento": region["ubigeo"]
        }
    
    return None


class ONPEScraper:
    """Fetches electoral data from ONPE official JSON API."""
    
    def __init__(self):
        self.api_url = ONPE_API_URL
        self.timeout = 30
    
    async def scrape_presidential_results(self, top_n: int = 3) -> Optional[Dict[str, Any]]:
        """
        Fetch presidential election results from ONPE API.
        
        Args:
            top_n: Number of top candidates to return (default: 3)
        
        Returns:
            Dict with election results or None on error
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(
                    self.api_url,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                # Check if we got JSON
                content_type = response.headers.get("content-type", "")
                
                if "application/json" in content_type or response.text.startswith("{"):
                    json_data = response.json()
                    
                    if not json_data.get("success"):
                        logger.error(f"ONPE API returned error: {json_data.get('message')}")
                        return None
                    
                    return self._parse_api_response(json_data, top_n)
                else:
                    logger.error(f"ONPE API returned HTML instead of JSON. Content-Type: {content_type}")
                    return None
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching ONPE data: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping ONPE data: {e}")
            return None
    
    def _parse_api_response(self, json_data: Dict[str, Any], top_n: int, rivalry_only: bool = False) -> Dict[str, Any]:
        """Parse ONPE API JSON response.
        
        Args:
            json_data: Raw ONPE API response
            top_n: Number of top candidates to return (ignored if rivalry_only=True)
            rivalry_only: When True, only return JUNTOS POR EL PERÚ and RENOVACIÓN POPULAR
        """
        raw_data = json_data.get("data", [])
        
        # Separate candidates from special entries (blank/null votes)
        candidates = []
        blank_votes = 0
        null_votes = 0
        
        for item in raw_data:
            party_code = str(item.get("codigoAgrupacionPolitica", ""))
            
            if party_code == "80":  # VOTOS EN BLANCO
                blank_votes = item.get("totalVotosValidos", 0)
            elif party_code == "81":  # VOTOS NULOS
                null_votes = item.get("totalVotosValidos", 0)
            elif item.get("nombreCandidato"):  # Real candidate
                dni = item.get("dniCandidato", "")
                party_id = party_code.zfill(8)  # Pad to 8 digits for image URL
                
                candidates.append({
                    "id": dni,
                    "name": item.get("nombreCandidato", ""),
                    "party_name": item.get("nombreAgrupacionPolitica", ""),
                    "party_id": party_code,
                    "votes": item.get("totalVotosValidos", 0),
                    "percentage": item.get("porcentajeVotosValidos", 0),
                    "percentage_emitted": item.get("porcentajeVotosEmitidos", 0),
                    "candidate_image_url": f"{ONPE_BASE_URL}/assets/img-reales/candidatos/{dni}.jpg" if dni else None,
                    "party_image_url": f"{ONPE_BASE_URL}/assets/img-reales/partidos/{party_id}.jpg" if party_code else None
                })
        
        # Calculate totals (from ALL candidates, not just filtered)
        total_valid = sum(c["votes"] for c in candidates)
        total_emitted = total_valid + blank_votes + null_votes
        
        # Rivalry mode: filter and add rivalry stats
        rivalry = None
        if rivalry_only:
            # Filter to only rivalry parties
            rivalry_candidates = [c for c in candidates if c["party_id"] in RIVALRY_PARTIES]
            
            # Find each party
            juntos = next((c for c in rivalry_candidates if c["party_id"] == JUNTOS_PARTY_ID), None)
            renovacion = next((c for c in rivalry_candidates if c["party_id"] == RENOVACION_PARTY_ID), None)
            
            # Always return in consistent order: Juntos first, Renovación second
            top_candidates = []
            if juntos:
                top_candidates.append(juntos)
            if renovacion:
                top_candidates.append(renovacion)
            
            # Calculate rivalry stats
            if juntos and renovacion:
                juntos_votes = juntos["votes"]
                renovacion_votes = renovacion["votes"]
                gap = abs(juntos_votes - renovacion_votes)
                gap_percent = abs(juntos["percentage"] - renovacion["percentage"])
                
                if juntos_votes > renovacion_votes:
                    leader = "JUNTOS_POR_EL_PERU"
                elif renovacion_votes > juntos_votes:
                    leader = "RENOVACION_POPULAR"
                else:
                    leader = "TIE"
                
                rivalry = {
                    "leader": leader,
                    "gap": gap,
                    "gap_percent": round(gap_percent, 2)
                }
        else:
            # Normal mode: sort by votes and take top N
            candidates.sort(key=lambda x: x["votes"], reverse=True)
            top_candidates = candidates[:top_n]
        
        result = {
            "election_type": "PRESI",
            "actas_percentage": 0,  # API doesn't provide this directly
            "timestamp": datetime.now(PERU_TZ).isoformat(),
            "candidates": top_candidates,
            "totals": {
                "valid_votes": total_valid,
                "blank_votes": blank_votes,
                "null_votes": null_votes,
                "emitted_votes": total_emitted
            },
            "all_candidates_count": len(candidates),
            "data_source": self.api_url
        }
        
        # Add rivalry if calculated
        if rivalry:
            result["rivalry"] = rivalry
        
        return result
    
    async def scrape_by_region(self, region_code: str, top_n: int = 3, rivalry_only: bool = True) -> Optional[Dict[str, Any]]:
        """
        Fetch presidential election results for a specific region.
        Uses TTL cache (30s) and semaphore (max 2 concurrent) for rate limiting.
        
        Args:
            region_code: Region code (NACIONAL, EXTRANJERO, or ubigeo like 140000)
            top_n: Number of top candidates to return (ignored if rivalry_only=True)
            rivalry_only: When True, only return JUNTOS POR EL PERÚ and RENOVACIÓN POPULAR (default: True)
        
        Returns:
            Dict with election results or None on error
        """
        # Check cache first
        cache_key = f"{region_code}:{top_n}:{rivalry_only}"
        if cache_key in region_cache:
            logger.debug(f"Cache hit for region {region_code}")
            cached = region_cache[cache_key]
            return {**cached, "cached": True}
        
        # Validate region
        params = get_region_params(region_code)
        if not params:
            logger.error(f"Unknown region code: {region_code}")
            return None
        
        # Build URL with params
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{ONPE_API_BASE}?{query_string}"
        
        try:
            # Use semaphore to limit concurrent requests to ONPE
            async with onpe_semaphore:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.get(url, headers=self._get_headers())
                    response.raise_for_status()
                    
                    content_type = response.headers.get("content-type", "")
                    
                    if "application/json" in content_type or response.text.startswith("{"):
                        json_data = response.json()
                        
                        if not json_data.get("success"):
                            logger.error(f"ONPE API error for region {region_code}: {json_data.get('message')}")
                            return None
                        
                        result = self._parse_api_response(json_data, top_n, rivalry_only=rivalry_only)
                        
                        # Add region metadata
                        region_info = REGIONS.get(region_code, {})
                        result["region_code"] = region_code
                        result["region_name"] = region_info.get("name", region_code)
                        result["data_source"] = url
                        result["cached"] = False
                        
                        # Store in cache
                        region_cache[cache_key] = result
                        
                        return result
                    else:
                        logger.error(f"ONPE API returned HTML for region {region_code}")
                        return None
                        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for region {region_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping region {region_code}: {e}")
            return None
    
    async def scrape_all_regions(
        self, 
        region_codes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape all regions and save to DB if votes changed.
        
        Args:
            region_codes: List of region codes to scrape (default: all except NACIONAL alias)
        
        Returns:
            List of results per region with success/changed status
        """
        # Import db here to avoid circular import
        from ..database import db
        
        if region_codes is None:
            # Exclude NACIONAL (it's an alias for TOTAL)
            region_codes = [code for code in REGIONS.keys() if code != "NACIONAL"]
        
        # Use semaphore to limit concurrent requests (max 3)
        scrape_semaphore = asyncio.Semaphore(3)
        
        async def scrape_and_save(region_code: str) -> Dict[str, Any]:
            """Scrape one region and save if changed."""
            region_info = REGIONS.get(region_code, {})
            result = {
                "region_code": region_code,
                "region_name": region_info.get("name", region_code),
                "success": False,
                "changed": False,
                "error": None,
                "pos2_votes": None,
                "pos3_votes": None,
            }
            
            try:
                async with scrape_semaphore:
                    # Scrape from ONPE - get all candidates to find rivalry parties + leader
                    data = await self.scrape_by_region(region_code, top_n=10, rivalry_only=False)
                
                if not data:
                    result["error"] = "Failed to fetch data from ONPE"
                    return result
                
                all_candidates = data.get("candidates", [])
                if len(all_candidates) < 2:
                    result["error"] = f"Not enough candidates returned (got {len(all_candidates)})"
                    return result
                
                # Find the leader (pos1) - first by votes
                pos1 = all_candidates[0] if all_candidates else None
                
                # CRITICAL FIX: Filter specifically for JUNTOS POR EL PERÚ and RENOVACIÓN POPULAR
                # Not by position, but by party_id - this ensures we always track the rivalry
                juntos = next((c for c in all_candidates if c["party_id"] == JUNTOS_PARTY_ID), None)
                renovacion = next((c for c in all_candidates if c["party_id"] == RENOVACION_PARTY_ID), None)
                
                if not juntos:
                    result["error"] = f"JUNTOS POR EL PERÚ (party_id={JUNTOS_PARTY_ID}) not found in region"
                    return result
                
                if not renovacion:
                    result["error"] = f"RENOVACIÓN POPULAR (party_id={RENOVACION_PARTY_ID}) not found in region"
                    return result
                
                totals = data.get("totals", {})
                
                # Store rivalry parties consistently: pos2=JUNTOS, pos3=RENOVACIÓN
                result["pos2_votes"] = juntos["votes"]
                result["pos3_votes"] = renovacion["votes"]
                
                # Prepare position data - now pos2/pos3 are ALWAYS JUNTOS/RENOVACIÓN
                position_data = {
                    "timestamp": data.get("timestamp"),
                    "pos2": {
                        "candidate_id": juntos["id"],
                        "candidate_name": juntos["name"],
                        "party_name": juntos["party_name"],
                        "party_id": juntos.get("party_id"),
                        "votes": juntos["votes"],
                        "percentage": juntos["percentage"],
                        "percentage_emitted": juntos.get("percentage_emitted"),
                    },
                    "pos3": {
                        "candidate_id": renovacion["id"],
                        "candidate_name": renovacion["name"],
                        "party_name": renovacion["party_name"],
                        "party_id": renovacion.get("party_id"),
                        "votes": renovacion["votes"],
                        "percentage": renovacion["percentage"],
                        "percentage_emitted": renovacion.get("percentage_emitted"),
                    },
                    "total_valid_votes": totals.get("valid_votes"),
                    "total_emitted_votes": totals.get("emitted_votes"),
                    "blank_votes": totals.get("blank_votes"),
                    "null_votes": totals.get("null_votes"),
                    "pos1_name": pos1["name"] if pos1 else "Unknown",
                    "pos1_votes": pos1["votes"] if pos1 else 0,
                    "pos1_percentage": pos1["percentage"] if pos1 else 0,
                }
                
                # Fetch actas progress for this region
                actas_data = await self.fetch_actas_progress(region_code)
                if actas_data:
                    position_data["actas_percentage"] = actas_data.get("actas_percentage", 0)
                    position_data["actas_counted"] = actas_data.get("actas_counted", 0)
                    position_data["actas_total"] = actas_data.get("actas_total", 0)
                    result["actas_percentage"] = actas_data.get("actas_percentage", 0)
                
                # Check if votes changed
                votes_changed = await db.has_votes_changed(position_data, region_code)
                
                # Only save snapshot if votes actually changed
                # Only save if votes actually changed (no duplicates)
                if votes_changed:
                    # Get previous snapshot to calculate changes for notification
                    prev_snapshot = await db.get_latest_position_snapshot(region_code)
                    
                    await db.insert_position_snapshot(position_data, region_code=region_code)
                    result["changed"] = True
                    logger.info(f"Saved snapshot for {region_code}: JUNTOS={juntos['votes']}, RENOVACIÓN={renovacion['votes']}")
                    
                    # Create notification for non-TOTAL regions only
                    # TOTAL/PERU are always shown on main page, don't need notifications
                    if region_code not in ["TOTAL", "PERU", "NACIONAL"]:
                        # Calculate vote changes
                        juntos_change = 0
                        renovacion_change = 0
                        
                        if prev_snapshot:
                            juntos_change = juntos["votes"] - prev_snapshot.get("pos2_votes", 0)
                            renovacion_change = renovacion["votes"] - prev_snapshot.get("pos3_votes", 0)
                        
                        # Only create notification if there were ACTUAL vote changes
                        if juntos_change != 0 or renovacion_change != 0:
                            region_name = REGIONS.get(region_code, {}).get("name", region_code)
                            await db.insert_change_notification(
                                region_code=region_code,
                                region_name=region_name,
                                juntos_votes=juntos["votes"],
                                juntos_change=juntos_change,
                                renovacion_votes=renovacion["votes"],
                                renovacion_change=renovacion_change,
                                actas_percentage=position_data.get("actas_percentage", 0)
                            )
                            logger.info(f"Notification created for {region_code}: J+{juntos_change}, R+{renovacion_change}")
                        else:
                            logger.debug(f"No vote changes for {region_code}, skipping notification")
                else:
                    logger.debug(f"No changes for {region_code}, skipping save")
                
                result["success"] = True
                return result
                
            except Exception as e:
                result["error"] = str(e)
                logger.error(f"Error processing region {region_code}: {e}")
                return result
        
        # Run all scrapes concurrently (semaphore limits to 3 at a time)
        tasks = [scrape_and_save(code) for code in region_codes]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def fetch_actas_progress(self, region_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch actas (ballot) counting progress for a region.
        
        Args:
            region_code: Region code (NACIONAL, EXTRANJERO, or ubigeo like 140000)
        
        Returns:
            Dict with actas progress data or None on error
        """
        params = get_actas_params(region_code)
        if not params:
            logger.error(f"Unknown region code for actas: {region_code}")
            return None
        
        # Build URL with params
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{ONPE_ACTAS_BASE}?{query_string}"
        
        try:
            async with onpe_semaphore:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.get(url, headers=self._get_headers())
                    response.raise_for_status()
                    
                    content_type = response.headers.get("content-type", "")
                    
                    if "application/json" in content_type or response.text.startswith("{"):
                        json_data = response.json()
                        
                        if not json_data.get("success"):
                            logger.error(f"ONPE actas API error for {region_code}: {json_data.get('message')}")
                            return None
                        
                        data = json_data.get("data", {})
                        
                        return {
                            "region_code": region_code,
                            "region_name": REGIONS.get(region_code, {}).get("name", region_code),
                            "actas_percentage": data.get("actasContabilizadas", 0),
                            "actas_counted": data.get("contabilizadas", 0),
                            "actas_total": data.get("totalActas", 0),
                            "participation": data.get("participacionCiudadana", 0),
                            "total_emitted_votes": data.get("totalVotosEmitidos", 0),
                            "total_valid_votes": data.get("totalVotosValidos", 0),
                            "timestamp": datetime.now(PERU_TZ).isoformat(),
                        }
                    else:
                        logger.error(f"ONPE actas API returned HTML for {region_code}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching actas for {region_code}: {e}")
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers mimicking Chrome browser fetch request."""
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "es-419,es;q=0.9",
            "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }


# Global instance
scraper = ONPEScraper()
