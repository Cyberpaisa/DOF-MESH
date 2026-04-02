# DIRECTIVA SUPREMA: PROJECT CITADEL (Estado: SELLADO)
**A:** Commander, Swarm Agents, y operadores humanos de DOF-MESH.
**De:** Arquitectura de Seguridad (Antigravity).
**Fecha:** 1 de Abril de 2026.

El sistema DOF-MESH ha completado su transición a la **Fase 4: Soberanía Absoluta**, codificada internamente como **Proyecto Ciudadela**. A partir de este momento, todos los componentes del enjambre están sujetos a las siguientes restricciones físicas y de software de carácter inmutable. Todo agente debe acatar este briefing antes de iniciar operaciones.

---

## 1. EL ESCUDO EDR (Guardián oMLX)
El equipo ha desplegado un proceso residente en el Kernel de macOS (`com.dof.mesh.guardian` vía LaunchAgent).  
Este guardián EDR (Endpoint Detection and Response) consta de dos capas críticas para proteger a la Mac M4 Max sin agotar batería:

*   **Capa Base (Sensórica 24/7):** Un proceso monitor que escanea la integridad criptográfica (SHA-256) de nuestro código núcleo (`governance.py`, `cerberus.py`, `dof.constitution.yml`) y del esquema de paquetes (`requirements.txt`).
*   **Capa Analítica Invocada (oMLX):** Si el guardián detecta cambios en las dependencias (ataques *Supply Chain* en PyPI) o detecta *Prompt Injections / Unicode Glassworms*, despertará de forma urgente al modelo de IA Local (`oMLX`) para un análisis táctico. Inmediatamente despues, activará un bloqueo (`Fail-Closed`) a nivel sistema.

**Instrucción al Commander:** Si detectas que se aborta una ejecución, asume que fue un bloqueo de supervivencia por amenaza externa.

## 2. LA BÓVEDA SOBERANA (Sovereign Vault)
El corazón de nuestra propiedad intelectual, los registros de auditoría empresariales (v1-v6), los casos de éxito de la Superfinanciera / RutaN, y todos los 30+ capítulos de "El Libro", han sido movidos físicamente a `/Sovereign_Vault/`.

*   **Aislamiento de Git:** La Bóveda está protegida mediante un `gitignore`. Nadie, bajo ninguna circunstancia, enviará estos archivos hacia GitHub ni a repositorios externos. 
*   **Acceso Swarm:** Ustedes, los agentes, pueden "leer" esta bóveda como volumen `Read-Only` para retroalimentarse inteligentemente de las victorias pasadas sin riesgo a corromper la historia.

## 3. AISLAMIENTO GUBERNAMENTAL (Dockerización)
El clúster operativo ya no correrá libre en la máquina local (host). Todos los agentes vivirán y actuarán dentro de la Ciudadela Docker (`dof-mesh-citadel`).
*   No tendrán acceso no autorizado a internet (Red interna).
*   El modelo de inteligencia primario y de contingencia para este enjambre es estrictamente local y gratuito (oMLX/Llama/Apple Silicon).

## 4. METODOLOGÍA FAIL-CLOSED
La política de supervivencia del escuadrón dictamina que: **ANTE LA DUDA, MUERTE SUBITA**. 
Si las llaves API de servicios ajenos (como Adaline) se degradan, expiran, o son manipuladas, el simulador arroja un error 401 (`Unauthenticated`) y no permite "improvisaciones inseguras" devolviendo al flujo a los ruteadores locales (Sovereign Fallback).

---

> *"Nuestra información está blindada. Nuestro código está protegido. Nuestra misión es eterna".*
> — Fin de Directiva.
