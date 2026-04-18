# Squad Team

> vigilante_electoral — Electoral monitoring application

## Coordinator

| Name | Role | Notes |
|------|------|-------|
| Squad | Coordinator | Routes work, enforces handoffs and reviewer gates. |

## Members

| Name | Role | Charter | Status |
|------|------|---------|--------|
| 🏗️ Alejandro | Lead | [charter](agents/alejandro/charter.md) | ✅ Active |
| ⚛️ Kate | Frontend Dev | [charter](agents/kate/charter.md) | ✅ Active |
| 🔧 Matt | Backend Dev | [charter](agents/matt/charter.md) | ✅ Active |
| 🧪 Silvio | Tester | [charter](agents/silvio/charter.md) | ✅ Active |
| � Reggie | Security | [charter](agents/reggie/charter.md) | ✅ Active |
| �📋 Scribe | Scribe | [charter](agents/scribe/charter.md) | ✅ Active |
| 🔄 Ralph | Work Monitor | [charter](agents/ralph/charter.md) | ✅ Active |


## Coding Agent

<!-- copilot-auto-assign: false -->

| Name | Role | Charter | Status |
|------|------|---------|--------|
| @copilot | Coding Agent | — | 🤖 Coding Agent |

### Capabilities

**🟢 Good fit — auto-route when enabled:**
- Bug fixes with clear reproduction steps
- Test coverage (adding missing tests, fixing flaky tests)
- Lint/format fixes and code style cleanup
- Dependency updates and version bumps
- Small isolated features with clear specs
- Boilerplate/scaffolding generation
- Documentation fixes and README updates

**🟡 Needs review — route to @copilot but flag for squad member PR review:**
- Medium features with clear specs and acceptance criteria
- Refactoring with existing test coverage
- API endpoint additions following established patterns
- Migration scripts with well-defined schemas

**🔴 Not suitable — route to squad member instead:**
- Architecture decisions and system design
- Multi-system integration requiring coordination
- Ambiguous requirements needing clarification
- Security-critical changes (auth, encryption, access control)
- Performance-critical paths requiring benchmarking
- Changes requiring cross-team discussion

## Project Context

- **Project:** vigilante_electoral
- **User:** Aaron
- **Created:** 2026-04-18
- **Stack:** FastAPI backend, Next.js 16 frontend, Supabase (database), Vercel (deployment)
- **Purpose:** Monitor electoral results from Peru's ONPE website, track vote changes over time
- **Data Source:** https://resultadoelectoral.onpe.gob.pe/main/presidenciales (updates every 15 min)
