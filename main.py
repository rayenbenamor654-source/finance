from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st


TND = Decimal("0.001")


# ---------- Calculations ----------
def money(value):
    return Decimal(str(value)).quantize(TND, rounding=ROUND_HALF_UP)


def format_tnd(value):
    """Format dinars with French separators and three decimal places."""
    formatted = f"{money(value):,.3f}"
    return formatted.replace(",", " ").replace(".", ",") + " TND"


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
    page_title="Finance | Tableau de bord",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
      :root {
        --ink: #20354a;
        --muted: #718096;
        --teal: #167c70;
        --teal-dark: #11675e;
        --canvas: #f2f0e9;
        --surface: #faf9f5;
        --line: #e4e0d5;
        --gold: #c49a53;
      }
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      .stApp { background: var(--canvas); color: var(--ink); }
      [data-testid="stHeader"] { background: rgba(242, 240, 233, .92); }
      [data-testid="stSidebar"] { background: #20384b; border-right: 1px solid #304a5c; }
      [data-testid="stSidebar"] * { color: #f2f0e9 !important; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c2d0d5 !important; }
      [data-testid="stSidebar"] hr { border-color: #496070; }
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #bdcbd0 !important; }
      h1, h2, h3 { font-family: 'Manrope', sans-serif; color: var(--ink); letter-spacing: -.035em; }
      .stMainBlockContainer { padding-top: 2rem; }
      .estimate-heading {
        margin: 0 0 1rem; padding-left: .75rem; border-left: 4px solid var(--teal);
        font-size: 1.6rem; font-weight: 800; line-height: 1.25;
      }
      .hero {
        position: relative; overflow: hidden; padding: 1.8rem 2rem; border-radius: 20px;
        margin: .15rem 0 1.7rem; color: #f7f5ef;
        background: linear-gradient(118deg, #20384b 0%, #27665f 100%);
        box-shadow: 0 14px 34px rgba(32, 56, 75, .13);
        animation: page-enter .52s cubic-bezier(.2,.7,.25,1) both;
      }
      .hero:after {
        content: ''; position: absolute; width: 240px; height: 240px; border-radius: 50%;
        right: -65px; top: -130px; border: 1px solid rgba(242,240,233,.17);
        box-shadow: 0 0 0 24px rgba(242,240,233,.035), 0 0 0 50px rgba(242,240,233,.025);
      }
      .hero h1 { color: #f7f5ef; margin: 0 0 .4rem; font-size: 2rem; }
      .hero p { color: #d7e2dc; margin: 0; font-size: 1rem; }
      .eyebrow { text-transform: uppercase; letter-spacing: .15em; color: #d8bd83;
                 font-weight: 700; font-size: .72rem; margin-bottom: .5rem; }
      .section-card { background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
                      padding: 1.2rem 1.35rem; margin-bottom: 1rem; box-shadow: 0 5px 16px rgba(32,53,74,.035); }
      [data-testid="stVerticalBlockBorderWrapper"] { background: var(--surface); border-radius: 16px; }
      [data-testid="stMetric"] {
        background: var(--surface); border: 1px solid var(--line); border-radius: 15px;
        padding: 1.05rem 1.2rem; box-shadow: 0 5px 16px rgba(32,53,74,.035);
        animation: metric-enter .55s ease both;
      }
      [data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
      [data-testid="stMetricValue"] { color: var(--teal); font-family: 'Manrope', sans-serif; }
      div.stButton > button[kind="primary"] { background: var(--teal); border: 0; border-radius: 10px; }
      div.stButton > button[kind="primary"]:hover { background: var(--teal-dark); }
      div[data-testid="stNumberInput"] input, div[data-testid="stDateInput"] input { border-radius: 9px; }
      .small-note { color: var(--muted); font-size: .87rem; }
      [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
      @keyframes page-enter {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
      }
      @keyframes metric-enter {
        0% { opacity: 0; transform: translateY(8px); }
        65% { opacity: .8; }
        100% { opacity: 1; transform: translateY(0); }
      }
      @media (prefers-reduced-motion: reduce) {
        *, *:before, *:after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## ◈ FINANCE")
    st.markdown("Votre espace de calcul financier")
    st.markdown("---")
    st.markdown("**ESPACE DE TRAVAIL**")
    page = st.radio(
        "Navigation",
        ["1 · Calcul d’intérêt", "2 · Compte d’épargne"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Calculs indicatifs · Vérifiez les conditions de votre établissement.")


# ---------- Page 1: simple interest ----------
if page == "1 · Calcul d’intérêt":
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 01</div>"
        "<h1>Calcul d’intérêt simple</h1>"
        "<p>Une estimation claire du rendement de votre capital, selon la durée choisie.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Simulateur de rendement")
    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            capital = c1.number_input("Capital initial (TND)", min_value=0.0, value=0.0, step=100.0)
            annual_rate = c2.number_input("Taux annuel (%)", min_value=0.0, value=5.0, step=0.25)
            c3, c4 = st.columns(2)
            duration = c3.number_input("Durée", min_value=0.0, value=2.0, step=0.5)
            unit = c4.selectbox("Unité de durée", ["Années", "Mois", "Jours"])
            st.markdown(
                "<p class='small-note'>Base de calcul : année commerciale de 360 jours pour une durée en jours.</p>",
                unsafe_allow_html=True,
            )

    with right:
        if duration > 0:
            interest, final_capital, _ = simple_interest(
                capital, annual_rate, duration, unit
            )
            st.markdown(
                "<h2 class='estimate-heading'>Votre estimation</h2>",
                unsafe_allow_html=True,
            )
            st.metric("Intérêts générés", format_tnd(interest))
            st.metric("Capital final estimé", format_tnd(final_capital))
        else:
            st.info("Saisissez une durée supérieure à zéro pour afficher l’estimation.")

    with st.expander("À propos de la méthode"):
        st.write(
            "Les intérêts simples sont calculés uniquement sur le capital initial : "
            "**I = C × t × n**, où C est le capital, t le taux annuel sous forme décimale "
            "et n la durée exprimée en années. Les intérêts ne sont pas capitalisés."
        )


# ---------- Page 2: savings account ----------
else:
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 02</div>"
        "<h1>Compte d’épargne</h1>"
        "<p>Suivez les mouvements et estimez les intérêts annuels selon la règle des quinzaines.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Vue d’ensemble du compte")
    c1, c2, c3 = st.columns(3)
    year = int(c1.number_input("Année civile", min_value=1900, max_value=2100, value=2025))
    initial = c2.number_input("Solde au 1er janvier (TND)", min_value=0.0, value=0.0, step=100.0)
    rate = c3.number_input("Taux annuel (%)", min_value=0.01, value=5.0, step=0.25)

    st.markdown("### Activité du compte")
    count = int(st.number_input("Nombre d’opérations", min_value=0, max_value=100, value=0, step=1))
    operations = []

    if count == 0:
        st.markdown(
            "<div class='section-card'><b>Aucun mouvement pour le moment</b><br>"
            "<span class='small-note'>L’estimation sera calculée sur la base du solde initial.</span></div>",
            unsafe_allow_html=True,
        )

    for index in range(count):
        with st.container(border=True):
            st.markdown(f"**Mouvement {index + 1:02d}**")
            cols = st.columns([1.2, 1, 1, 0.8])
            operation_date = cols[0].date_input(
                "Date de l’opération",
                value=date(year, 1, 1),
                min_value=date(year, 1, 1),
                max_value=date(year, 12, 31),
                key=f"savings_date_{index}",
            )
            operation_type = cols[1].selectbox(
                "Type de mouvement", ["Versement", "Retrait"], key=f"savings_type_{index}"
            )
            amount = cols[2].number_input(
                "Montant (TND)", min_value=0.0, value=100.0, step=50.0,
                key=f"savings_amount_{index}",
            )
            cols[3].markdown("<br>", unsafe_allow_html=True)
            cols[3].caption(f"Date valeur : {value_date(operation_date, operation_type).strftime('%d/%m/%Y')}")
            operations.append((operation_date, operation_type, amount))

    try:
        result = calculate_savings(initial, rate, operations, year)
        st.markdown("### Synthèse annuelle")
        m1, m2, m3 = st.columns(3)
        m1.metric("Solde hors intérêts", format_tnd(result["balance"]))
        m2.metric("Intérêts estimés", format_tnd(result["interest"]))
        m3.metric("Capital acquis", format_tnd(result["capital"]))

        st.markdown("### Détail du calcul")
        rows = [
            {
                "Du": start.strftime("%d/%m/%Y"),
                "Au": end.strftime("%d/%m/%Y"),
                "Solde (TND)": float(money(balance)),
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

        with st.expander("Comprendre la règle des quinzaines"):
            st.write(
                "Un versement prend effet le 1er ou le 16 selon sa date d’opération. "
                "Un retrait est pris en compte au début de la quinzaine correspondante. "
                "Les intérêts sont calculés sur les soldes successifs, avec une année commerciale de 360 jours."
            )
    except ValueError as error:
        st.error(str(error))
