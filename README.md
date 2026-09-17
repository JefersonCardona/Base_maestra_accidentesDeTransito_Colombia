## **Observatorio de Accidentalidad Vial en Colombia: Integración de Datos para la Toma de Decisiones**

**Jeferson Cardona — Daniela Baena**

Introducción a la Analítica de Negocios -
Universidad de Antioquia

## **Problemática**

Los siniestros viales en Colombia son una de las principales causas de muerte en el
país, un problema que no ha disminuido pese a los esfuerzos institucionales. Solo en
2024 se registraron 8.479 muertes por siniestros viales, una tasa de 16,09
fallecidos por cada 100.000 habitantes, cifra que se mantiene en un nivel
históricamente alto tras el repunte que siguió a la pandemia (Instituto Nacional de
Medicina Legal y Ciencias Forenses [INMLCF], 2026).

En Colombia, como respuesta a esta problemática, se cuenta con el Observatorio
Nacional de Seguridad Vial (ONSV), administrado por la Agencia Nacional de
Seguridad Vial (ANSV), que se encarga de recopilar, analizar y divulgar información
sobre los siniestros viales que ocurren en el país (Agencia Nacional de Seguridad
Vial [ANSV], s. f.). Pese a que existe una fuente oficial de información, esta
suele presentar estadísticas descriptivas de una sola fuente a la vez, sin integrar
variables de otras entidades (población, contexto económico y laboral) que
permitan explicar por qué la siniestralidad se concentra en determinados
territorios o perfiles de víctima.

Esta es la necesidad de información que busca cubrir el presente observatorio: no
duplicar las estadísticas ya publicadas, sino construir, a partir de la integración
de varias fuentes, indicadores y relaciones que apoyen decisiones de priorización  de intervenciones de seguridad vial
por parte de entidades públicas y privadas.


## Cómo ejecutar

1. Abre `Proyecto_integrador_Entrega_2_DanielaBaena_JefersonCardona.ipynb` en Jupyter o en Google Colab.
2. Ejecuta las celdas en orden, de arriba hacia abajo — cada sección depende de que la anterior ya haya corrido.
3. Necesitas conexión a internet: el notebook descarga los datos en vivo desde `datos.gov.co` y `dane.gov.co`, no usa archivos locales. La descarga completa toma unos minutos por el volumen de registros (más de 400.000 entre las dos fuentes).
4. Al final, el notebook genera automáticamente el archivo `base_maestra_accidentalidad_colombia.csv` en la misma carpeta donde lo estés corriendo.

## Dónde encontrar la base de datos

- **Ya construida, para consulta rápida:** [Ver en Google Drive](https://drive.google.com/file/d/1scXzoYoH9dImZJhG4sTJjZ6BrST2TvKb/view?usp=drive_link) *(no se subió el CSV completo al repositorio por su tamaño)*.
- **Generada desde cero:** corriendo el notebook completo como se indica arriba, queda disponible como `base_maestra_accidentalidad_colombia.csv`.

## Documentación del proceso

Para el detalle de la problemática, las preguntas de análisis, el proceso de extracción y la integración de las fuentes, ver el informe [`Informe_entrega2_DanielaBaena_JefersonCardona.pdf`](./Informe_entrega2_DanielaBaena_JefersonCardona.pdf) incluido en este repositorio.
