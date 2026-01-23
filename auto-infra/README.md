# Auto-Infrastructure Platform

Dynamic auto-scaling infrastructure for hostscience.io, blazebase.io, and adtelco.io

## Architecture

**Hybrid Go + n8n system:**
- Go daemons for performance-critical monitoring and provisioning
- n8n workflows for orchestration and business logic

## Components

### Go Daemons
- `capacity-monitor`: Real-time capacity tracking (80% threshold triggers)
- `provisioning-agent`: Customer environment provisioning
- `resource-cleanup`: Idle resource detection and cleanup

### n8n Workflows
- Auto-scaling (15-20% expansion/contraction)
- Customer onboarding (hostscience.io, blazebase.io)
- Resource cleanup orchestration

## Target Budget: $1,100/month OCI
