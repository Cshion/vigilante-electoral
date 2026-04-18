# Kate — History

## Project Context

**Project:** vigilante_electoral — Electoral monitoring application
**User:** Aaron
**Stack:** FastAPI backend, Next.js 16 frontend, Supabase (database), Vercel (deployment)
**Purpose:** Monitor and track electoral results from Peru's ONPE website, showing vote changes over time

## Key Files

- (to be populated as project develops)

## Learnings

### RegionSelector Redesign (2026-04-18)
- Redesigned from separated buttons to **connected segmented control** (iOS/Material-inspired)
- Key design decisions:
  - Connected pills with shared borders - first segment gets `rounded-l-lg`, last gets `rounded-r-lg`
  - Active state: `bg-blue-600 text-white` with subtle shadow
  - Inactive state: `bg-white text-gray-600` with hover states
  - Removed the visual separator (vertical line) - connected design doesn't need it
- Dropdown improvements:
  - Added sticky header with "Departamentos" label
  - Mobile-responsive: dropdown aligns right on mobile (`right-0 sm:left-0`)
  - Subtle entrance animation with `animate-in fade-in slide-in-from-top-2`
- All functionality preserved: close on escape, close on click outside, onRegionChange callback

## Patterns

- (document patterns discovered during work)
