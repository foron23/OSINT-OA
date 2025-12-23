# 🔍 Herramientas OSINT (Sin API Keys)

Este documento contiene la lista de herramientas OSINT integradas y recomendaciones para futuras ampliaciones.

## 📊 Herramientas Implementadas

| Herramienta | Propósito | Estado |
|-------------|-----------|--------|
| **Maigret** | Búsqueda de usernames en 500+ plataformas | ✅ Implementado |
| **BBOT** | Enumeración de subdominios, web recon, emails | ✅ Implementado |
| **Holehe** | Verificación de emails en 100+ sitios | ✅ Implementado |
| **Amass** | OWASP subdomain enumeration + intel | ✅ Implementado |
| **PhoneInfoga** | OSINT de números telefónicos | ✅ Implementado |
| **DuckDuckGo** | Búsqueda web sin API key | ✅ Implementado |
| **BeautifulSoup** | Web scraping | ✅ Implementado |

---

## 🆕 Herramientas Recomendadas para Futuras Versiones

### 1. ~~**Holehe** - Verificación de Emails en Plataformas~~ ✅ IMPLEMENTADO
> Ya integrado como `HoleheEmailTool` en `tools/holehe.py`

### 2. **Sherlock** - Búsqueda de Usernames
- **GitHub:** https://github.com/sherlock-project/sherlock
- **Propósito:** Busca usernames en 400+ redes sociales
- **Sin API Key:** ✅ Sí
- **Instalación:** `pip install sherlock-project`
- **Uso CLI:**
  ```bash
  sherlock username --output results.json --print-found
  ```
- **Prioridad:** ⭐⭐ Media (similar a Maigret, puede usarse como verificación cruzada)
- **Tipo de datos:** Perfiles de redes sociales

### 3. **theHarvester** - Reconocimiento de Dominios
- **GitHub:** https://github.com/laramies/theHarvester
- **Propósito:** Recolecta emails, subdominios, IPs, URLs de un dominio
- **Sin API Key:** ✅ Parcial (fuentes pasivas funcionan sin API)
- **Instalación:** `pip install theHarvester`
- **Uso CLI:**
  ```bash
  theHarvester -d example.com -b duckduckgo,crtsh,dnsdumpster -f output
  ```
- **Fuentes sin API Key:**
  - `duckduckgo` - Búsqueda web
  - `crtsh` - Certificate Transparency logs
  - `dnsdumpster` - DNS records
  - `rapiddns` - Subdominios
  - `urlscan` - URLs escaneadas
- **Prioridad:** ⭐⭐⭐ Alta (complementa BBOT)
- **Tipo de datos:** Emails, subdominios, IPs

### 4. **Subfinder** - Enumeración de Subdominios (Rápido)
- **GitHub:** https://github.com/projectdiscovery/subfinder
- **Propósito:** Descubrimiento de subdominios ultra-rápido
- **Sin API Key:** ✅ Parcial (funciona con fuentes pasivas)
- **Instalación:** 
  ```bash
  go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
  ```
- **Uso CLI:**
  ```bash
  subfinder -d example.com -silent -o subdomains.txt
  ```
- **Prioridad:** ⭐⭐ Media (alternativa más rápida a BBOT para subdominios)
- **Tipo de datos:** Subdominios

### 5. **Httpx** - Sondeo de Servicios HTTP
- **GitHub:** https://github.com/projectdiscovery/httpx
- **Propósito:** Verifica qué servicios HTTP están activos, obtiene tecnologías
- **Sin API Key:** ✅ Sí
- **Instalación:**
  ```bash
  go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
  ```
- **Uso CLI:**
  ```bash
  cat subdomains.txt | httpx -tech-detect -status-code -json -o results.json
  ```
- **Prioridad:** ⭐⭐⭐ Alta (excelente complemento para análisis de subdominios)
- **Tipo de datos:** Tecnologías web, códigos de estado, títulos

### 6. **Waybackurls** - URLs Históricas
- **GitHub:** https://github.com/tomnomnom/waybackurls
- **Propósito:** Obtiene URLs del dominio desde Wayback Machine
- **Sin API Key:** ✅ Sí
- **Instalación:**
  ```bash
  go install github.com/tomnomnom/waybackurls@latest
  ```
- **Uso CLI:**
  ```bash
  echo "example.com" | waybackurls > urls.txt
  ```
- **Prioridad:** ⭐⭐ Media (útil para encontrar endpoints ocultos)
- **Tipo de datos:** URLs históricas, endpoints

### 7. **Nuclei** - Escáner de Vulnerabilidades
### 7. **Nuclei** - Escáner de Vulnerabilidades
- **GitHub:** https://github.com/projectdiscovery/nuclei
- **Propósito:** Detección de vulnerabilidades con templates
- **Sin API Key:** ✅ Sí
- **Instalación:**
  ```bash
  go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
  ```
- **Uso CLI:**
  ```bash
  nuclei -u https://example.com -severity medium,high,critical -j -o results.json
  ```
- **Prioridad:** ⭐⭐⭐ Alta (detección activa de vulnerabilidades)
- **Tipo de datos:** Vulnerabilidades, misconfigs
- **⚠️ Nota:** Es un escáner activo, usar con precaución

### 8. **SpiderFoot** - Framework OSINT Completo
- **GitHub:** https://github.com/smicallef/spiderfoot
- **Propósito:** Framework OSINT todo-en-uno con módulos gratuitos
- **Sin API Key:** ✅ Parcial (200+ módulos, muchos funcionan sin API)
- **Instalación:** `pip install spiderfoot`
- **Uso CLI:**
  ```bash
  python sf.py -s example.com -t DOMAIN -m sfp_dnsresolve,sfp_whois -f JSON
  ```
- **Prioridad:** ⭐⭐ Media (puede ser redundante con herramientas actuales)
- **Tipo de datos:** Múltiple (emails, subdominios, IPs, etc.)

### 9. ~~**Phoneinfoga** - OSINT de Números Telefónicos~~ ✅ IMPLEMENTADO
> Ya integrado como `PhoneInfogaScanTool` en `tools/phoneinfoga.py`

### 10. ~~**Amass** - Mapeo de Superficies de Ataque~~ ✅ IMPLEMENTADO
> Ya integrado como `AmassEnumTool` y `AmassIntelTool` en `tools/amass.py`

---

## 📋 Priorización Actualizada

### ✅ Ya Implementados
1. **Holehe** - Verificación de emails ✅
2. **Amass** - Subdomain enumeration + intel ✅
3. **PhoneInfoga** - OSINT de teléfonos ✅

### 🔜 Próximas Implementaciones Recomendadas
1. **theHarvester** - Más fuentes de datos para dominios
2. **Httpx** - Análisis de servicios HTTP
3. **Sherlock** - Verificación cruzada de usernames
4. **Subfinder** - Alternativa rápida para subdominios

### 📌 Avanzado (Requiere consideración especial)
5. **Nuclei** - Escaneo de vulnerabilidades (requiere permisos)
6. **SpiderFoot** - Framework completo

---

## 🏗️ Arquitectura de Integración Actual

```
┌─────────────────────────────────────────────────────────────────┐
│                         OSINT OA                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Persona   │  │   Dominio   │  │   General   │             │
│  │   Tools     │  │   Tools     │  │   Tools     │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐             │
│  │ Maigret     │  │ BBOT        │  │ DuckDuckGo  │             │
│  │ Sherlock    │  │ theHarvester│  │ Scraping    │             │
│  │ Holehe      │  │ Subfinder   │  │ Waybackurls │             │
│  │ Phoneinfoga │  │ Amass       │  │             │             │
│  │             │  │ Httpx       │  │             │             │
│  │             │  │ Nuclei      │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Plantilla para Nueva Herramienta

```python
# tools/new_tool.py
"""
New OSINT Tool Integration

Tool: ToolName
GitHub: https://github.com/...
Purpose: Description
No API Key: Yes/Partial
"""

from typing import Optional, Dict, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import asyncio
import subprocess
import json
import tempfile
import os

class ToolNameInput(BaseModel):
    """Input schema for ToolName."""
    target: str = Field(description="Target to analyze")
    # Add other parameters

class ToolNameTool(BaseTool):
    """LangChain tool for ToolName."""
    
    name: str = "tool_name"
    description: str = """Description of what the tool does.
    
    Input: target (e.g., example.com)
    Output: JSON with findings
    """
    args_schema: type = ToolNameInput
    
    def _run(self, target: str) -> str:
        """Synchronous execution."""
        return asyncio.run(self._run_async(target))
    
    async def _arun(self, target: str) -> str:
        """Asynchronous execution."""
        return await self._run_async(target)
    
    async def _run_async(self, target: str) -> str:
        """Execute the tool."""
        # Check if tool is installed
        if not await self._check_installed():
            return json.dumps({
                "error": "ToolName not installed",
                "install": "pip install toolname"
            })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "output.json")
            
            cmd = [
                "toolname",
                target,
                "--json",
                "--output", output_file
            ]
            
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                _, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=300
                )
                
                if os.path.exists(output_file):
                    with open(output_file) as f:
                        return f.read()
                
                return json.dumps({"error": stderr.decode()})
                
            except asyncio.TimeoutError:
                return json.dumps({"error": "Timeout", "partial": True})
            except Exception as e:
                return json.dumps({"error": str(e)})
    
    async def _check_installed(self) -> bool:
        """Check if tool is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "toolname", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return proc.returncode == 0
        except:
            return False
```

---

## 📝 Notas Importantes

1. **Modo Pasivo vs Activo**: Algunas herramientas (Nuclei, BBOT) pueden hacer escaneos activos. Asegurarse de tener permisos antes de usar en modo activo.

2. **Rate Limiting**: Muchas APIs gratuitas tienen límites. Implementar delays entre requests.

3. **Dependencias Go**: Varias herramientas (subfinder, httpx, nuclei, amass) están escritas en Go. El Dockerfile necesitará incluir el runtime de Go o usar binarios pre-compilados.

4. **Combinación de Resultados**: Implementar un consolidador que combine y deduplique resultados de múltiples herramientas.

5. **Caché de Resultados**: Cachear resultados para evitar consultas repetidas al mismo target.

---

## 📚 Referencias

- [OSINT Framework](https://osintframework.com/) - Mapa de herramientas OSINT
- [Awesome OSINT](https://github.com/jivoi/awesome-osint) - Lista curada de herramientas
- [IntelTechniques](https://inteltechniques.com/tools/) - Recursos OSINT
