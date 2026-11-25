from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st


EURO = Decimal("0.01")


# ---------- Calculations ----------
def money(value):
    return Decimal(str(value)).quantize(EURO, rounding=ROUND_HALF_UP)


def format_eur(value):
    """Format euros with French separators."""
    formatted = f"{money(value):,.2f}"
    return formatted.replace(",", " ").replace(".", ",") + " €"


def simple_interest(capital, annual_rate_percent, duration, unit):
    """Calculate simple interest using a 360-day commercial year."""
    capital = Decimal(str(capital))
    rate = Decimal(str(annual_rate_percent)) / Decimal("100")
    duration = Decimal(str(duration))
    year_fraction = {
        "Années": duration,
        "Mois": duration / Decimal("12"),
        "Jours": duration / Decimal("360"),
    }[unit]
    interest = money(capital * rate * year_fraction)
    return interest, money(capital + interest), year_fraction


def next_month(value):
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def value_date(operation_date, operation_type):
    """Apply the savings account's half-month value-date convention."""
    if operation_type not in ("Versement", "Retrait"):
        raise ValueError("Type d'opération invalide.")

    if operation_type == "Versement":
        if operation_date.day in (1, 16):
            return operation_date
        if operation_date.day < 16:
            return date(operation_date.year, operation_date.month, 16)
        return next_month(operation_date)

    if operation_date.day <= 15:
        return date(operation_date.year, operation_date.month, 1)
    return date(operation_date.year, operation_date.month, 16)


def days_360(start, end):
    """Return the number of days using a 30/360 commercial calendar."""
    return (
        (end.year - start.year) * 360
        + (end.month - start.month) * 30
        + min(end.day, 30)
        - min(start.day, 30)
    )


def calculate_savings(initial_balance, annual_rate, operations, year):
    balance = Decimal(str(initial_balance))
    rate = Decimal(str(annual_rate))
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    valued_operations = []
    segments = []

    for operation_date, operation_type, amount in operations:
        amount = Decimal(str(amount))
        if amount < 0:
            raise ValueError("Le montant d'une opération ne peut pas être négatif.")
        signed_amount = amount if operation_type == "Versement" else -amount
        valued_operations.append(
            (value_date(operation_date, operation_type), operation_date, operation_type, signed_amount)
        )

    valued_operations.sort(key=lambda item: (item[0], item[1], item[2]))
    segment_start = start

    for value, operation_date, operation_type, signed_amount in valued_operations:
        if value < start:
            value = start
        if value >= end:
            continue

        days = days_360(segment_start, value)
        if days > 0:
            number = balance * Decimal(days) / Decimal("100")
            segments.append((segment_start, value, balance, days, number))

        balance += signed_amount
        if balance < 0:
            raise ValueError(
                f"Le retrait du {operation_date.strftime('%d/%m/%Y')} dépasse le solde disponible à sa date de valeur."
            )
        segment_start = value

    days = days_360(segment_start, end)
    if days > 0:
        number = balance * Decimal(days) / Decimal("100")
        segments.append((segment_start, end, balance, days, number))

    total_numbers = sum((segment[4] for segment in segments), Decimal("0"))
    if rate <= 0:
        raise ValueError("Le taux annuel doit être supérieur à zéro.")

    divisor = Decimal("360") / rate
    interest = money(total_numbers / divisor)
    return {
        "balance": balance,
        "interest": interest,
        "capital": money(balance + interest),
        "total_numbers": total_numbers,
        "divisor": divisor,
        "segments": segments,
    }


# ---------- App setup and visual style ----------
st.set_page_config(
    page_title="Finance | Calculs d'intérêts",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
      :root { --ink: #172b4d; --muted: #64748b; --green: #11856b; --line: #e6edf2; }
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      .stApp { background: #f5f8fa; color: var(--ink); }
      [data-testid="stSidebar"] { background: #102a43; }
      [data-testid="stSidebar"] * { color: #f3f7fa !important; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #bed0dc !important; }
      h1, h2, h3 { font-family: 'Manrope', sans-serif; color: var(--ink); letter-spacing: -0.035em; }
      .hero { padding: 1.65rem 1.9rem; border-radius: 20px; margin: .2rem 0 1.5rem;
              background: linear-gradient(120deg, #102a43 0%, #174e57 100%); color: white; }
      .hero h1 { color: white; margin: 0 0 .35rem; font-size: 2rem; }
      .hero p { color: #d3e2e8; margin: 0; font-size: 1rem; }
      .eyebrow { text-transform: uppercase; letter-spacing: .14em; color: #85d5bb;
                 font-weight: 700; font-size: .72rem; margin-bottom: .45rem; }
      .section-card { background: white; border: 1px solid var(--line); border-radius: 16px;
                      padding: 1.2rem 1.35rem; margin-bottom: 1rem; }
      [data-testid="stMetric"] { background: white; border: 1px solid var(--line); border-radius: 14px;
                                  padding: 1rem 1.15rem; }
      [data-testid="stMetricLabel"] { color: #64748b; }
      [data-testid="stMetricValue"] { color: #11856b; font-family: 'Manrope', sans-serif; }
      div.stButton > button[kind="primary"] { background: #11856b; border: 0; border-radius: 10px; }
      div.stButton > button[kind="primary"]:hover { background: #0c6d57; }
      div[data-testid="stNumberInput"] input, div[data-testid="stDateInput"] input { border-radius: 9px; }
      .small-note { color: #64748b; font-size: .87rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 📊 Finance")
    st.markdown("Outils de calcul financier")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["1 · Calcul d’intérêt", "2 · Compte d’épargne"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Calculs indicatifs — vérifiez les conventions applicables à votre établissement.")


# ---------- Page 1: simple interest ----------
if page == "1 · Calcul d’intérêt":
    st.markdown(
        "<div class='hero'><div class='eyebrow'>Outil financier · 01</div>"
        "<h1>Calcul d’intérêt simple</h1>"
        "<p>Estimez les intérêts générés par un capital sur une durée donnée.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Paramètres du calcul")
    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            capital = c1.number_input("Capital initial (€)", min_value=0.01, value=1000.0, step=100.0)
            annual_rate = c2.number_input("Taux annuel (%)", min_value=0.0, value=5.0, step=0.25)
            c3, c4 = st.columns(2)
            duration = c3.number_input("Durée", min_value=0.0, value=2.0, step=0.5)
            unit = c4.selectbox("Unité de durée", ["Années", "Mois", "Jours"])
            st.markdown(
                "<p class='small-note'>Pour les jours, le calcul utilise une année commerciale de 360 jours.</p>",
                unsafe_allow_html=True,
            )

    with right:
        year_fraction = Decimal("0")
        if duration > 0:
            interest, final_capital, year_fraction = simple_interest(
                capital, annual_rate, duration, unit
            )
            st.markdown("### Résultat")
            st.metric("Intérêts simples", format_eur(interest))
            st.metric("Capital final estimé", format_eur(final_capital))
            st.markdown(
                f"<div class='section-card'><b>Formule</b><br><span class='small-note'>"
                f"I = C × t × n<br>"
                f"{format_eur(capital)} × {annual_rate:.2f} % × {year_fraction:.4f} an(s)"
                f"</span></div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Saisissez une durée supérieure à zéro pour afficher le résultat.")

    with st.expander("Comprendre le calcul"):
        st.write(
            "Les intérêts simples sont calculés uniquement sur le capital initial : "
            "**I = C × t × n**, où C est le capital, t le taux annuel sous forme décimale "
            "et n la durée exprimée en années. Les intérêts ne sont pas capitalisés."
        )


# ---------- Page 2: savings account ----------
else:
    st.markdown(
        "<div class='hero'><div class='eyebrow'>Outil financier · 02</div>"
        "<h1>Compte d’épargne</h1>"
        "<p>Calculez les intérêts annuels selon la méthode des quinzaines et la base 30/360.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Paramètres du compte")
    c1, c2, c3 = st.columns(3)
    year = int(c1.number_input("Année civile", min_value=1900, max_value=2100, value=2025))
    initial = c2.number_input("Solde au 1er janvier (€)", min_value=0.0, value=1000.0, step=100.0)
    rate = c3.number_input("Taux annuel (%)", min_value=0.01, value=5.0, step=0.25)

    st.markdown("### Mouvements du compte")
    count = int(st.number_input("Nombre d’opérations", min_value=0, max_value=100, value=0, step=1))
    operations = []

    if count == 0:
        st.markdown(
            "<div class='section-card'><b>Aucune opération ajoutée</b><br>"
            "<span class='small-note'>Le calcul sera effectué sur le solde initial de l’année.</span></div>",
            unsafe_allow_html=True,
        )

    for index in range(count):
        with st.container(border=True):
            st.markdown(f"**Opération {index + 1}**")
            cols = st.columns([1.2, 1, 1, 0.8])
            operation_date = cols[0].date_input(
                "Date de l’opération",
                value=date(year, 1, 1),
                min_value=date(year, 1, 1),
                max_value=date(year, 12, 31),
                key=f"savings_date_{index}",
            )
            operation_type = cols[1].selectbox(
                "Type", ["Versement", "Retrait"], key=f"savings_type_{index}"
            )
            amount = cols[2].number_input(
                "Montant (€)", min_value=0.0, value=100.0, step=50.0,
                key=f"savings_amount_{index}",
            )
            cols[3].markdown("<br>", unsafe_allow_html=True)
            cols[3].caption(f"Date valeur : {value_date(operation_date, operation_type).strftime('%d/%m/%Y')}")
            operations.append((operation_date, operation_type, amount))

    try:
        result = calculate_savings(initial, rate, operations, year)
        st.markdown("### Synthèse annuelle")
        m1, m2, m3 = st.columns(3)
        m1.metric("Solde hors intérêts", format_eur(result["balance"]))
        m2.metric("Intérêts estimés", format_eur(result["interest"]))
        m3.metric("Capital acquis", format_eur(result["capital"]))

        st.markdown("### Détail du calcul")
        rows = [
            {
                "Du": start.strftime("%d/%m/%Y"),
                "Au": end.strftime("%d/%m/%Y"),
                "Solde (€)": float(money(balance)),
                "Jours (30/360)": days,
                "Nombres": float(money(number)),
            }
            for start, end, balance, days, number in result["segments"]
        ]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune période de calcul n’est disponible pour ces paramètres.")

        summary1, summary2 = st.columns(2)
        summary1.markdown(f"**Total des nombres :** {money(result['total_numbers']):,.2f}")
        summary2.markdown(f"**Diviseur :** {result['divisor']:,.4f}")

        with st.expander("Règle des quinzaines"):
            st.write(
                "Un versement prend effet le 1er ou le 16 selon sa date d’opération. "
                "Un retrait est pris en compte au début de la quinzaine correspondante. "
                "Les intérêts sont calculés sur les soldes successifs, avec une année commerciale de 360 jours."
            )
    except ValueError as error:
        st.error(str(error))
