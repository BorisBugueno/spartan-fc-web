# 🛡️ Spartan FC · Plataforma de Estadísticas

Web móvil para consultar posiciones, fixture, goleadores y asistencias del club Spartan FC en las categorías **Serie 35** y **Serie 45**. Se actualiza automáticamente al modificar `data/Resultados.xlsx` y hacer `git push` a GitHub.

---

## 📁 Estructura del proyecto

```
spartan-fc-web/
├── app.py                 # App Streamlit (toda la lógica)
├── requirements.txt       # Dependencias Python
├── .streamlit/
│   └── config.toml        # Tema Spartan (negro/dorado)
├── data/
│   └── Resultados.xlsx    # Tu fixture. Editarlo actualiza la web.
├── assets/
│   └── Logo_Oficial.jpeg
└── README.md
```

---

## 🧩 Cómo se llenan los datos en el Excel

Respeta exactamente las columnas actuales:

| Fecha   | Local        | Goles L | vs  | Goles V | Visita        | Goles Spartan    | Asistencia Spartan |
|---------|--------------|---------|-----|---------|---------------|------------------|--------------------|
| Fecha 1 | Corinthians  | 1       | vs  | 1       | Spartan F.C.  | Sady             | Pita               |
| Fecha 2 | Julieta      | 0       | vs  | 3       | Spartan F.C.  | Sady, Sady, Pepe | Pita, Pita         |

**Reglas importantes** (basadas en cómo funciona `app.py`):

1. **Partidos no jugados**: dejas `Goles L` y `Goles V` vacíos. No entran al cálculo de posiciones.
2. **Fecha libre**: pon `LIBRE` como equipo rival. El script la ignora.
3. **Filas separadoras**: puedes dejar las filas con `---` entre fechas; se ignoran.
4. **Múltiples goleadores en un partido**: separa por coma o punto y coma.  
   Ejemplo: `Sady, Sady, Pepe` = Sady marcó 2 goles y Pepe 1.
5. **El nombre `Spartan F.C.`** se usa para detectar tus partidos. No cambies ese texto.

El script **recalcula automáticamente**:
- PJ, PG, PE, PP, GF, GC, DIF y Pts (3 por victoria, 1 por empate)
- Ordena por Pts → DIF → GF
- Tabla de goleadores y asistencias de jugadores de Spartan

---

## 🚀 Deployment: subir a GitHub y Streamlit Cloud

### Paso 1 — Crear el repositorio en GitHub

1. Entra a [github.com](https://github.com) e inicia sesión.
2. Click en **+ → New repository**.
3. Nombre: `spartan-fc-web` · Tipo: **Public** · No marques "Initialize with README".
4. Crear el repo.

### Paso 2 — Subir los archivos (modo simple, sin usar terminal)

En la página del repo recién creado:

1. Click en **uploading an existing file** (enlace azul en el centro).
2. Arrastra las carpetas y archivos del proyecto:
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - carpeta `.streamlit/` completa
   - carpeta `data/` completa (con el Excel)
   - carpeta `assets/` completa (con el logo)
3. Abajo, commit message: `Primer release`.
4. Click en **Commit changes**.

> Alternativa por terminal (si te manejas con git):
> ```bash
> cd spartan-fc-web
> git init
> git add .
> git commit -m "Primer release"
> git branch -M main
> git remote add origin https://github.com/TU_USUARIO/spartan-fc-web.git
> git push -u origin main
> ```

### Paso 3 — Desplegar en Streamlit Community Cloud

1. Entra a [share.streamlit.io](https://share.streamlit.io).
2. Inicia sesión **con tu cuenta de GitHub** y autoriza el acceso.
3. Click **New app** → **Deploy a public app from GitHub**.
4. Completa:
   - **Repository**: `TU_USUARIO/spartan-fc-web`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL (opcional)**: `spartan-fc` (te dará `spartan-fc.streamlit.app`)
5. Click **Deploy**. Primera vez tarda ~2 minutos mientras instala dependencias.

**Ya tienes tu link público** (algo como `https://spartan-fc.streamlit.app`) para compartir con los jugadores. Funciona perfecto en celular.

---

## 🔄 Cómo actualizar resultados cada semana

Opción A — **Desde el navegador (la más simple)**:
1. Ve a tu repo en GitHub → entra a la carpeta `data/`.
2. Click en `Resultados.xlsx` → botón de lápiz ✏️ o **Delete** y vuelves a subir uno editado.
   Alternativa más directa: en la página principal del repo, arrastra el `.xlsx` nuevo encima. GitHub detectará que es un update y lo reemplazará.
3. Commit con mensaje "Actualizo fecha N".
4. Streamlit Cloud rebuilda solo. La web se refresca en ~60 segundos.

Opción B — **Con terminal y git**:
```bash
# Después de editar el Excel localmente
git add data/Resultados.xlsx
git commit -m "Resultados fecha N"
git push
```

---

## 🎨 Personalización rápida

| Qué quieres cambiar         | Dónde tocar                             |
|-----------------------------|-----------------------------------------|
| Colores del tema            | `.streamlit/config.toml` + CSS en `app.py` (bloque `CUSTOM_CSS`) |
| Nombre del club detectado   | Variable `SPARTAN_NAME` en `app.py`     |
| Tiempo de cache de datos    | Parámetro `ttl=60` en `@st.cache_data`  |
| Texto del subtítulo         | `hero` en la función `main()`           |

---

## 🧪 Probar localmente (opcional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abre `http://localhost:8501` en tu navegador.

---

## ❓ Problemas comunes

- **"File not found: Resultados.xlsx"** → te faltó subir la carpeta `data/`. Verifica en GitHub que exista `data/Resultados.xlsx`.
- **Un equipo no aparece en la tabla** → revisa que no tenga partidos jugados (o que tenga el nombre idéntico en todas las fechas). Los espacios en blanco al final no afectan.
- **Spartan no aparece resaltado** → revisa que escribas exactamente `Spartan F.C.` (con la abreviatura tal cual).
- **App duerme tras inactividad** → Streamlit Cloud pausa apps sin uso. El primer usuario del día espera ~10s para que despierte. Gratis; no afecta a jugadores que entren después.
