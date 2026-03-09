# Monitor Deportivo Pro — Streamlit Edition

Adaptación del UserScript de Tampermonkey a una app web local con Streamlit.

## Características

- **32 medios deportivos** (16 nacionales + 16 internacionales)
- **Análisis semántico Jaccard** — detecta exclusivos y faltantes por TEMA, no por título exacto
- **Tendencias** — clustering automático de temas que cubren varios medios simultáneamente
- **Comparativa Olé vs competencia** — exclusivos, ausentes y compartidos
- **IA con Claude** — análisis general y informe editorial específico para Olé

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
streamlit run app.py
```

Luego abrir en el navegador: `http://localhost:8501`

## Funcionamiento

1. **Ingresá tu API key** de Anthropic en el panel izquierdo (opcional, solo para análisis IA)
2. **Hacé clic en ↺ Actualizar fuentes** para cargar los titulares
3. Navegá por las pestañas:
   - **🇦🇷 Nacionales** — medios argentinos con filtro por texto
   - **🌍 Internacionales** — medios del mundo
   - **⭐ Olé vs Todos** — análisis semántico: exclusivos, faltantes, compartidos
   - **📊 Tendencias** — temas que cubren múltiples medios
   - **🤖 Análisis IA** — informes generados por Claude

## Notas técnicas

- Los fetches se hacen en paralelo (10 workers) para mayor velocidad
- El análisis semántico usa similitud de Jaccard con umbral 0.22
- Las fuentes RSS se parsean con `beautifulsoup4` (parser `xml`)
- Sin API key de Anthropic, todas las funciones de scraping y análisis semántico funcionan igual
