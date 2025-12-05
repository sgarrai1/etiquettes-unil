import streamlit as st
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, portrait, A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import os
import unicodedata


# ---------------------------
# FONCTION DE NORMALISATION
# ---------------------------
def normalize_text(s):
    if not isinstance(s, str):
        s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("utf-8")
    return s.lower().strip()


# ---------------------------
# COULEURS PAR CATÉGORIE
# ---------------------------
COULEURS_CATEGORIES = {
    "Acide": "#D32F2F",
    "Base": "#64B5F6",
    "Métaux lourd": "#E0E0E0",
    "Halogéné": "#FFEB3B",
    "Solution aqueuse": "#D7BDE2",
    "Non halogéné": "#A5D6A7"
}


# ---------------------------
# CHARGEMENT BASE PRODUITS
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "produits.csv")

try:
    produits = pd.read_csv(CSV_PATH, encoding="utf-8-sig", sep=",")
    produits.columns = produits.columns.str.strip().str.lower()
    if "nom" not in produits.columns or "omod" not in produits.columns:
        raise ValueError("Le CSV doit contenir les colonnes : nom, omod.")
except Exception as e:
    st.error(f"Erreur de chargement de la base produits : {e}")
    st.stop()

if "couleur" not in produits.columns:
    produits["couleur"] = "#FFFFFF"

produits["nom_normalise"] = produits["nom"].astype(str).apply(normalize_text)


# ---------------------------
# SESSION STATE
# ---------------------------
if "matches_df" not in st.session_state:
    st.session_state.matches_df = pd.DataFrame()
if "choix_produit" not in st.session_state:
    st.session_state.choix_produit = None


# ---------------------------
# INTERFACE PRINCIPALE
# ---------------------------
logo_path = "UNIL-LOGOTYPE-BLUE-RGB.png"
col_logo, col_titre = st.columns([1, 4])
with col_logo:
    if os.path.exists(logo_path):
        st.image(logo_path, width=140)
with col_titre:
    st.markdown(
        """
        <h1 style="margin-bottom:0;">Création d’étiquette</h1>
        <h3 style="margin-top:0; font-weight:400;">Déchets chimiques — UNIL / SSTE</h3>
        """,
        unsafe_allow_html=True
    )


# ---------------------------
# RECHERCHE PRODUIT
# ---------------------------
st.markdown("### 1️⃣ Recherche d’un produit dans la base")
nom_produit = st.text_input("Nom du produit (ex. Acétone, Mercure...) :")

col1, col2 = st.columns(2)
with col1:
    if st.button("🔎 Rechercher"):
        query = normalize_text(nom_produit)
        if not query:
            st.warning("Veuillez saisir un nom avant de rechercher.")
        else:
            df = produits[produits["nom_normalise"].str.contains(query, na=False)].copy()
            if df.empty:
                st.session_state.matches_df = pd.DataFrame()
                st.session_state.choix_produit = None
                st.warning("Aucun produit trouvé dans la base.")
            else:
                st.session_state.matches_df = df
                st.session_state.choix_produit = df["nom"].iloc[0]

with col1:
    if st.button("📋 Afficher toute la base"):
        st.session_state.matches_df = produits.copy()
        st.info(f"Toute la base est affichée ({len(produits)} produits).")

if not st.session_state.matches_df.empty:
    st.info(f"{len(st.session_state.matches_df)} produit(s) trouvé(s). Cliquez pour sélectionner :")
    for i, row in st.session_state.matches_df.iterrows():
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"**{row['nom']}**  \nCode OMoD : {row['omod']}")
        with cols[1]:
            if st.button("Sélectionner", key=f"select_{i}"):
                st.session_state.choix_produit = row["nom"]
                st.success(f"✅ Produit sélectionné : {row['nom']}")


# ---------------------------
# SAISIE MANUELLE
# ---------------------------
st.markdown("### ✍️ Saisie manuelle (si produit non trouvé)")
nom_manuel = st.text_input("Nom du produit (manuel) :")
omod_manuel = st.text_input("Code OMoD (manuel) :")
categorie_couleur = st.selectbox(
    "Catégorie du produit (pour la couleur du fond) :",
    list(COULEURS_CATEGORIES.keys()),
    index=0
)


# ---------------------------
# INFOS UTILISATEUR
# ---------------------------
st.markdown("### 2️⃣ Informations à indiquer sur l’étiquette")
faculte = st.text_input("Faculté :")
num_remettant = st.text_input("N° de remettant :")
nom_createur = st.text_input("Nom du créateur :")
prenom_createur = st.text_input("Prénom du créateur :")
date = st.date_input("Date :")
infos_sup = st.text_area("Données supplémentaires sur le produit :")


# ---------------------------
# PICTOGRAMMES
# ---------------------------
st.markdown("### 3️⃣ Sélection des pictogrammes SGH")
pictogrammes_disponibles = [
    "SGH01", "SGH02", "SGH03", "SGH04", "SGH05",
    "SGH06", "SGH07", "SGH08", "SGH09"
]
cols = st.columns(3)
pictos_selectionnes = []
for i, picto in enumerate(pictogrammes_disponibles):
    with cols[i % 3]:
        path = f"pictos/{picto}.png"
        if os.path.exists(path):
            st.image(path, width=60)
        if st.checkbox(picto, key=f"chk_{picto}"):
            pictos_selectionnes.append(picto)


# ---------------------------
# FORMAT ÉTIQUETTE
# ---------------------------
st.markdown("### 🏷️ Format de l’étiquette")
formats_disponibles = {
    "Grande (140×100 mm – A4 paysage)": ("grand", 140, 100),
    "Moyenne (HERMA 96×50.8 mm – A4 portrait)": ("moyen", 96, 50.8)
}
format_label = st.selectbox("Choisissez le format :", list(formats_disponibles.keys()))
format_code, largeur_etiquette_mm, hauteur_etiquette_mm = formats_disponibles[format_label]

nb_max = 4 if format_code == "grand" else 8
nb_etiquettes = st.number_input(f"Nombre d’étiquettes à générer (1 à {nb_max}) :", 1, nb_max, 1)

if format_code == "grand":
    positions_dict = {1: "1️⃣ Haut gauche", 2: "2️⃣ Haut droite", 3: "3️⃣ Bas gauche", 4: "4️⃣ Bas droite"}
    positions_selectionnees = st.multiselect(
        "Position(s) sur la page :", options=list(positions_dict.keys()),
        format_func=lambda x: positions_dict[x],
        default=list(range(1, min(nb_etiquettes, 4) + 1))
    )
else:
    st.info("🧾 Pour ce format, les étiquettes seront placées automatiquement sur la feuille A4.")
    positions_selectionnees = None


# ---------------------------
# DESSIN D’UNE ÉTIQUETTE
# ---------------------------
def dessiner_etiquette(c, x0, y0, w, h, d, pictos):
    from reportlab.lib.colors import HexColor
    c.saveState()
    s = h / (100 * mm)

    # Bandeau haut
    bandeau_h = 0.12 * h
    bandeau_y = y0 + h - 0.15 * h
    c.setLineWidth(1)
    c.line(x0, bandeau_y + bandeau_h, x0 + w, bandeau_y + bandeau_h)
    c.line(x0, bandeau_y, x0, bandeau_y + bandeau_h)
    c.line(x0 + w, bandeau_y, x0 + w, bandeau_y + bandeau_h)

    # Logo UNIL
    logo_path = "UNIL-LOGOTYPE-BLUE-RGB.png"
    if os.path.exists(logo_path):
        logo_w = 0.25 * w
        logo_h = 0.12 * h
        lx = x0 + 0.05 * w
        ly = bandeau_y + (bandeau_h - logo_h) / 2
        c.drawImage(ImageReader(logo_path), lx, ly, width=logo_w, height=logo_h, mask='auto')

    # N° remettant
    c.setFont("Helvetica-Bold", 9 * s)
    c.drawString(x0 + 0.55 * w, bandeau_y + bandeau_h / 2 - 4 * s, f"N° remettant : {d['num_remettant']}")

    # Zone colorée du nom
    couleur_zone = d.get("couleur_fond", "#FFFFFF")
    try:
        c.setFillColor(HexColor(couleur_zone))
    except:
        c.setFillColor(HexColor("#FFFFFF"))
    c.rect(x0, y0 + h - 0.33 * h, w / 2, 0.09 * h, fill=True, stroke=0)
    c.setFillColorRGB(0, 0, 0)

    # Nom du produit
    c.setFont("Helvetica-Bold", 10 * s)
    produit = str(d["nom"]).strip()
    max_len = 35
    lignes_nom = [produit[i:i + max_len] for i in range(0, len(produit), max_len)]
    for i, ligne in enumerate(lignes_nom[:2]):
        c.drawCentredString(x0 + w / 4, y0 + h - 0.26 * h - i * (0.035 * h), ligne)

    c.setFont("Helvetica-Bold", 11 * s)
    c.drawCentredString(
        x0 + 3 * w / 4,              # Position horizontale (à droite)
        y0 + h - 0.30 * h,           # Plus haut qu'avant pour éviter les pictos
        f"Code OMoD : {d['omod']}"
    )

    # Pictogrammes — décalés à droite
    nb_pictos = min(len(pictos), 6)
    if nb_pictos > 0:
        picto_size = 0.12 * h
        cols = 3
        rows = (nb_pictos + cols - 1) // cols
        spacing_x = 0.02 * w
        spacing_y = 0.02 * h
        total_row_w = cols * picto_size + (cols - 1) * spacing_x
        start_x = x0 + (w / 2) + ((w / 2 - total_row_w) / 2)
        base_y = y0 + h - 0.52 * h

        for i, picto in enumerate(pictos[:6]):
            r = i // cols
            cidx = i % cols
            px = start_x + cidx * (picto_size + spacing_x)
            py = base_y - r * (picto_size + spacing_y)
            path = f"pictos/{picto}.png"
            if os.path.exists(path):
                c.drawImage(ImageReader(path), px, py, width=picto_size, height=picto_size, mask='auto')

    # Texte d’informations
    c.setFont("Helvetica", 10 * s)
    base_y = y0 + 0.18 * h
    c.drawString(x0 + 0.07 * w, base_y + 0.21 * h, f"Faculté : {d['faculte']}")
    c.drawString(x0 + 0.07 * w, base_y + 0.14 * h, f"Nom : {d['nom_createur']}")
    c.drawString(x0 + 0.07 * w, base_y + 0.07 * h, f"Prénom : {d['prenom_createur']}")
    c.drawString(x0 + 0.07 * w, base_y + 0.00 * h, f"Date : {d['date']}")

    # Données supplémentaires
    texte = str(d.get("infos_sup", "")).strip()
    if len(texte) > 100:
        texte = texte[:100] + "..."
    if texte:
        y_start = base_y - 0.03 * h
        c.drawString(x0 + 0.07 * w, y_start, "Données supplémentaires :")
        mots, lignes_sup, ligne = texte.split(), [], ""
        for mot in mots:
            if len((ligne + " " + mot).strip()) <= 45:
                ligne = (ligne + " " + mot).strip()
            else:
                if ligne:
                    lignes_sup.append(ligne)
                ligne = mot
        if ligne:
            lignes_sup.append(ligne)
        for i, l in enumerate(lignes_sup[:5]):
            c.drawString(x0 + 0.10 * w, y_start - (i + 1) * (0.045 * h), l)

    c.restoreState()


# ---------------------------
# GÉNÉRATION DU PDF
# ---------------------------
def generer_etiquettes_pdf(donnees, pictos, nb=4, pos_sel=None, lw_mm=140, lh_mm=100, format_code="grand"):
    if format_code == "grand":
        page_format = landscape(A4)
        cols, rows, nb_max = 2, 2, 4
        x_start, y_start, x_gap, y_gap = 5 * mm, 10 * mm, 10 * mm, 10 * mm
    else:
        page_format = portrait(A4)
        cols, rows, nb_max = 2, 4, 8
        x_start, y_start, x_gap, y_gap = 10 * mm, 10 * mm, 5 * mm, 5 * mm

    page_w, page_h = page_format
    lw, lh = lw_mm * mm, lh_mm * mm

    # 🔁 renommage automatique si fichier déjà ouvert
    base_filename = f"etiquettes_{normalize_text(donnees['nom'])}.pdf"
    filename = base_filename
    i = 1
    while os.path.exists(filename):
        filename = f"etiquettes_{normalize_text(donnees['nom'])}_{i}.pdf"
        i += 1

    c = canvas.Canvas(filename, pagesize=page_format)

    positions = []
    for r in range(rows):
        for cl in range(cols):
            x = x_start + cl * (lw + x_gap)
            y = y_start + r * (lh + y_gap)
            positions.append((x, page_h - y - lh))

    total = nb
    current = 0
    while current < total:
        for (x0, y0) in positions:
            if current >= total:
                break
            dessiner_etiquette(c, x0, y0, lw, lh, donnees, pictos)
            current += 1
        if current < total:
            c.showPage()

    c.save()
    return filename


# ---------------------------
# BOUTON DE GÉNÉRATION
# ---------------------------
if st.button("🧾 Générer le PDF"):
    utilise_base = st.session_state.choix_produit is not None
    if not utilise_base and (not nom_manuel.strip() or not omod_manuel.strip()):
        st.error("❌ Saisir un nom et un code OMoD ou choisir un produit existant.")
        st.stop()
    if not faculte or not nom_createur or not prenom_createur or not date:
        st.error("❌ Tous les champs faculté, nom, prénom et date sont obligatoires.")
        st.stop()
    if len(pictos_selectionnes) == 0:
        st.error("❌ Sélectionnez au moins un pictogramme.")
        st.stop()

    if utilise_base:
        sel = st.session_state.choix_produit
        m = produits[produits["nom"] == sel].iloc[0]
        nom_final, omod_final = str(m["nom"]), str(m["omod"])
        couleur_fond = m.get("couleur", "#FFFFFF")
    else:
        nom_final, omod_final = nom_manuel.strip(), omod_manuel.strip()
        couleur_fond = COULEURS_CATEGORIES.get(categorie_couleur, "#FFFFFF")

    donnees = {
        "nom": nom_final,
        "omod": omod_final,
        "faculte": faculte,
        "num_remettant": num_remettant,
        "nom_createur": nom_createur,
        "prenom_createur": prenom_createur,
        "date": date.strftime("%d/%m/%Y"),
        "infos_sup": infos_sup,
        "couleur_fond": couleur_fond
    }

    fichier = generer_etiquettes_pdf(
        donnees, pictos_selectionnes,
        nb_etiquettes, positions_selectionnees,
        largeur_etiquette_mm, hauteur_etiquette_mm,
        format_code
    )

    st.success(f"✅ Étiquettes générées pour {nom_final}")
    with open(fichier, "rb") as f:
        st.download_button("📄 Télécharger le PDF", f, file_name=fichier)


