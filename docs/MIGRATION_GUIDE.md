# Guía de Migración - OSINT News Aggregator

## Resumen de Cambios

Este documento describe los cambios realizados en la migración del sistema de agentes OSINT:

1. **pip → uv**: Gestor de paquetes más rápido
2. **LangChain → LangGraph Avanzado**: Observabilidad y human-in-the-loop
3. **OSRFramework → Maigret + bbot**: Herramientas OSINT modernas

---

## 1. Migración de pip a uv

### Problema
pip es lento para resolver dependencias, especialmente en entornos Docker donde cada rebuild descarga todo desde cero.

### Solución
Migración a [uv](https://github.com/astral-sh/uv), el gestor de paquetes Python más rápido (10-100x más rápido que pip).

### Cambios Realizados

#### `Dockerfile.prod` (Etapa Builder)
```dockerfile
# ANTES (pip)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn supervisor aiohttp

# DESPUÉS (uv)
ENV UV_VERSION=0.5.24
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"
RUN uv pip install --no-cache -r requirements.txt && \
    uv pip install --no-cache gunicorn supervisor aiohttp
```

#### `Dockerfile` (Desarrollo)
Mismos cambios aplicados para consistencia.

### Beneficios
- **Velocidad**: Instalación de dependencias ~10-100x más rápida
- **Resolución**: Mejor resolución de conflictos de dependencias
- **Cache**: Mejor manejo de cache de wheels

---

## 2. Migración a LangGraph Avanzado

### Problema
El uso básico de `create_react_agent` no aprovecha las capacidades avanzadas de LangGraph:
- Sin checkpoints para persistencia de estado
- Sin human-in-the-loop para revisión de operaciones sensibles
- Limitada observabilidad

### Solución
Implementación de grafos LangGraph avanzados con estados tipados, checkpoints y puntos de interrupción.

### Nuevo Módulo: `agents/langgraph_core.py`

#### Estados Tipados
```python
class InvestigationState(TypedDict):
    """Estado completo de una investigación OSINT."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    topic: str
    depth: str
    phase: InvestigationPhase
    findings: List[Dict[str, Any]]
    sources: List[str]
    indicators: List[str]
    requires_human_review: bool
    human_approved: bool
    review_reason: Optional[str]
    agents_used: List[str]
    start_time: str
    error: Optional[str]
```

#### Fases de Investigación
```python
class InvestigationPhase(str, Enum):
    PLANNING = "planning"      # Planificar estrategia
    COLLECTION = "collection"  # Recolectar información
    ANALYSIS = "analysis"      # Analizar hallazgos
    VERIFICATION = "verification"  # Revisión humana (opcional)
    REPORTING = "reporting"    # Generar reporte
    COMPLETE = "complete"      # Finalizado
```

#### Grafos Disponibles

1. **Simple ReAct Agent**
   ```python
   from agents import create_simple_react_agent
   
   graph = create_simple_react_agent(tools, system_prompt)
   result = await graph.ainvoke({"messages": [HumanMessage(content=query)]})
   ```

2. **Investigation Graph** (multi-fase con human-in-the-loop)
   ```python
   from agents import create_investigation_graph, run_investigation
   
   graph = create_investigation_graph(tools, human_review=True)
   result = await run_investigation(graph, topic="APT29", depth="deep")
   ```

### Beneficios
- **Estado persistente**: Checkpoints permiten resumir investigaciones
- **Human-in-the-loop**: Revisión humana antes de acciones sensibles
- **Observabilidad**: Compatible con LangSmith para tracing
- **Tipado fuerte**: Estados TypedDict para mejor DX

### Integración con LangSmith
```bash
# Variables de entorno para observabilidad
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=your-langsmith-api-key
export LANGCHAIN_PROJECT=osint-aggregator
```

---

## 3. Migración de OSRFramework a Maigret + bbot

### Problema
OSRFramework está deprecated y no se mantiene activamente desde 2021.

### Solución
Reemplazo con herramientas modernas y activamente mantenidas:
- **Maigret**: Username OSINT (reemplaza usufy)
- **bbot**: Attack surface enumeration (funcionalidad adicional)

### Archivos Eliminados
- `agents/osint/osrframework.py`
- `tools/osrframework.py`

### Nuevos Tools

#### Maigret (`tools/maigret.py`)
```python
from tools.maigret import MaigretUsernameTool, MaigretReportTool

# Búsqueda de username en 500+ plataformas
username_tool = MaigretUsernameTool()
result = await username_tool._arun("target_username", top_sites=100)

# Reporte completo de identidad
report_tool = MaigretReportTool()
report = await report_tool._arun("target_username")
```

#### bbot (`tools/bbot.py`)
```python
from tools.bbot import BbotSubdomainTool, BbotWebScanTool, BbotEmailTool

# Enumeración de subdominios
subdomain_tool = BbotSubdomainTool()
result = await subdomain_tool._arun("target.com", passive_only=True)

# Reconocimiento web
web_tool = BbotWebScanTool()
result = await web_tool._arun("target.com")

# Harvesting de emails
email_tool = BbotEmailTool()
result = await email_tool._arun("target.com")
```

### Nuevos Agentes

#### MaigretAgent (`agents/osint/maigret.py`)
```python
from agents import MaigretAgent

agent = MaigretAgent()
result = agent.run("Search for username 'john_doe_2024'")
```

Capacidades:
- Búsqueda de username en 500+ plataformas
- Correlación cross-platform
- Análisis de presencia online

#### BbotAgent (`agents/osint/bbot.py`)
```python
from agents import BbotAgent

agent = BbotAgent()
result = agent.run("Enumerate subdomains of example.com")
```

Capacidades:
- Enumeración de subdominios
- Detección de tecnologías web
- Harvesting de emails
- Mapeo de attack surface

### Comparación OSRFramework vs Nuevas Herramientas

| Característica | OSRFramework | Maigret | bbot |
|---------------|--------------|---------|------|
| Mantenimiento | ❌ Abandonado | ✅ Activo | ✅ Activo |
| Username OSINT | usufy (300+ sites) | ✅ 500+ sites | ❌ |
| Email verify | mailfy | ❌ | ✅ |
| Subdomain enum | ❌ | ❌ | ✅ |
| Web recon | ❌ | ❌ | ✅ |
| Attack surface | ❌ | ❌ | ✅ |
| Async support | ❌ | ✅ | ✅ |

---

## 4. Actualización de requirements.txt

### Dependencias Eliminadas
```diff
- osrframework>=0.20.0
```

### Dependencias Añadidas
```diff
+ langgraph-checkpoint>=2.0.0  # Para checkpoints y human-in-the-loop
+ langsmith>=0.2.0              # Para observabilidad
+ maigret>=0.4.4                # Username OSINT
+ bbot>=2.0.0                   # Attack surface enumeration
```

---

## 5. Guía de Uso Post-Migración

### Investigación Simple
```python
from agents import ControlAgent

control = ControlAgent()
result = control.investigate("Target organization", depth="standard")
print(result["report"])
```

### Investigación con LangGraph Avanzado
```python
from agents import create_investigation_graph, run_investigation
from tools import get_all_tools

# Crear grafo con revisión humana
graph = create_investigation_graph(
    tools=get_all_tools(),
    human_review=True
)

# Ejecutar investigación
result = await run_investigation(
    graph,
    topic="APT Group Analysis",
    depth="deep",
    thread_id="investigation-001"
)
```

### Username OSINT con Maigret
```python
from agents import MaigretAgent

agent = MaigretAgent()
result = agent.run("Investigate username 'suspicious_user'")
```

### Domain Recon con bbot
```python
from agents import BbotAgent

agent = BbotAgent()
result = agent.run("Map attack surface of target-domain.com")
```

---

## 6. Consideraciones de Seguridad

### Maigret
- Solo realiza búsquedas pasivas
- No intenta autenticación en ninguna plataforma
- Respeta límites de rate limiting

### bbot
- Por defecto usa modo pasivo (no escaneo activo)
- No realiza fuzzing o exploitation
- Requiere permiso explícito para escaneo activo

### Human-in-the-Loop
El nuevo sistema permite pausar investigaciones para revisión humana:
```python
graph = create_investigation_graph(tools, human_review=True)
```

Cuando se detectan hallazgos sensibles, el grafo pausará automáticamente para aprobación.

---

## 7. Troubleshooting

### Maigret no encontrado
```bash
# Instalar maigret
pip install maigret

# Verificar instalación
maigret --version
```

### bbot no encontrado
```bash
# Instalar bbot
pip install bbot

# Verificar instalación
bbot --version
```

### LangSmith no conecta
```bash
# Verificar variables de entorno
echo $LANGCHAIN_API_KEY
echo $LANGCHAIN_TRACING_V2

# Debe ser:
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=lsv2_...
```

---

## 8. Próximos Pasos

1. **Testing**: Ejecutar suite completa de tests
2. **Docker Build**: Validar construcción con uv
3. **Performance**: Medir mejoras de velocidad
4. **Observabilidad**: Configurar LangSmith dashboard
5. **Documentación**: Actualizar README principal

---

*Documento generado automáticamente durante la migración*
*Fecha: $(date)*
