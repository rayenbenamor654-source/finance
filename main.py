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


def compound_interest(capital, annual_rate_percent, duration_years, frequency):
    """Calculate compound interest with quarterly or semiannual capitalization."""
    capital = Decimal(str(capital))
    rate = Decimal(str(annual_rate_percent)) / Decimal("100")
    duration = Decimal(str(duration_years))
    periods_per_year = {"Trimestrielle": Decimal("4"), "Semestrielle": Decimal("2")}[frequency]

    if duration < 0:
        raise ValueError("La durée doit être positive ou égale à zéro.")
    if rate < 0:
        raise ValueError("Le taux annuel ne peut pas être négatif.")

    total_periods = duration * periods_per_year
    if total_periods != total_periods.to_integral_value():
        raise ValueError("La durée doit correspondre à des périodes complètes de capitalisation.")

    periodic_rate = rate / periods_per_year
    periods = int(total_periods)
    growth = (Decimal("1") + periodic_rate) ** periods
    final_capital = money(capital * growth)
    interest = money(final_capital - capital)
    return interest, final_capital, periodic_rate


def simple_interest(capital, annual_rate_percent, duration, unit):
    """Calculate simple interest using a 360-day commercial year."""
    capital = Decimal(str(capital))
    rate = Decimal(str(annual_rate_percent)) / Decimal("100")
    duration = Decimal(str(duration))
    if unit == "Jours" and duration != duration.to_integral_value():
        raise ValueError("La durée en jours doit être un nombre entier.")
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
        color-scheme: light;
        --ink: #172033;
        --muted: #667085;
        --violet: #7357d9;
        --violet-dark: #5b43b5;
        --teal: #087e72;
        --teal-light: #22a99a;
        --coral: #ef766a;
        --gold: #d7a43b;
        --canvas: #f7f4ed;
        --surface: #ffffff;
        --soft-violet: #eeeafd;
        --soft-coral: #fff0ed;
        --line: #e8e3d8;
      }
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      .stApp, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f8f6ef 0%, #f2f7f5 55%, #f7f1fa 100%);
        color: var(--ink);
      }
      [data-testid="stHeader"] { background: rgba(248, 246, 239, .92); }
      [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #087e72 0%, #22a99a 100%);
        border-right: 1px solid #087266;
      }
      [data-testid="stSidebar"] * { color: #ffffff !important; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #e2f7f3 !important; }
      [data-testid="stSidebar"] hr { border-color: rgba(255, 255, 255, .28); }
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #d8f3ef !important; }
      h1, h2, h3 { font-family: 'Manrope', sans-serif; color: var(--ink); letter-spacing: -.035em; }
      .stMainBlockContainer { padding-top: 2rem; }
      .estimate-heading {
        margin: 0 0 1rem; padding-left: .75rem; border-left: 4px solid var(--coral);
        font-size: 1.6rem; font-weight: 800; line-height: 1.25;
      }
      .hero {
        position: relative; overflow: hidden; padding: 1.8rem 2rem; border-radius: 20px;
        margin: .15rem 0 1.7rem; color: #ffffff;
        background: linear-gradient(118deg, #087e72 0%, #159889 55%, #22a99a 100%);
        box-shadow: 0 14px 34px rgba(8, 126, 114, .18);
        animation: page-enter .52s cubic-bezier(.2,.7,.25,1) both;
      }
      .hero:after {
        content: ''; position: absolute; width: 240px; height: 240px; border-radius: 50%;
        right: -65px; top: -130px; border: 1px solid rgba(255,255,255,.35);
        box-shadow: 0 0 0 24px rgba(255,255,255,.08), 0 0 0 50px rgba(255,255,255,.05);
      }
      .hero h1 { color: #ffffff; margin: 0 0 .4rem; font-size: 2rem; }
      .hero p { color: #e9fffb; margin: 0; font-size: 1rem; }
      .eyebrow { text-transform: uppercase; letter-spacing: .15em; color: #bff3e9;
                 font-weight: 800; font-size: .72rem; margin-bottom: .5rem; }
      .section-card {
        background: var(--surface); color: var(--ink); border: 1px solid var(--line); border-radius: 16px;
        padding: 1.2rem 1.35rem; margin-bottom: 1rem;
        box-shadow: 0 7px 20px rgba(115, 87, 217, .07);
      }
      [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
      }
      [data-testid="stMetric"] {
        background: linear-gradient(145deg, #ffffff 0%, #f7f5ff 100%);
        border: 1px solid #ddd6f5; border-radius: 15px;
        padding: 1.05rem 1.2rem; box-shadow: 0 7px 20px rgba(115,87,217,.08);
        animation: metric-enter .55s ease both;
      }
      [data-testid="stMetricLabel"] { color: #656d82; font-weight: 700; }
      [data-testid="stMetricValue"] { color: var(--violet); font-family: 'Manrope', sans-serif; }
      div.stButton > button[kind="primary"] {
        background: var(--violet); border: 0; border-radius: 10px; color: #ffffff;
      }
      div.stButton > button[kind="primary"]:hover { background: var(--violet-dark); }
      div[data-testid="stNumberInput"] input,
      div[data-testid="stDateInput"] input,
      div[data-testid="stSelectbox"] [role="combobox"] {
        color: var(--ink); background: #ffffff; border: 1px solid #dcd7e8; border-radius: 9px;
      }
      [data-testid="stWidgetLabel"] { color: var(--ink); }
      [data-testid="stCaptionContainer"] { color: var(--muted); }
      .small-note { color: var(--muted); font-size: .87rem; }
      [data-testid="stDataFrame"] {
        border: 1px solid #dfd8f1; border-radius: 12px; overflow: hidden;
      }
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
            unit = c4.selectbox("Unité de durée", ["Années", "Mois", "Jours"])
            if unit == "Jours":
                duration = c3.number_input(
                    "Durée", min_value=0, value=2, step=1, format="%d", key="duration_days"
                )
            else:
                duration = c3.number_input(
                    "Durée", min_value=0.0, value=2.0, step=0.5, key=f"duration_{unit}"
                )
            st.markdown(
                "<p class='small-note'>Base de calcul : année commerciale de 360 jours pour une durée en jours.</p>",
                unsafe_allow_html=True,
            )

    with right:
        if duration > 0:
            interest, final_capital, _ = simple_interest(
                capital, annual_rate, duration, unit
            )
            st.markdown("<h2 class='estimate-heading'>Votre estimation</h2>", unsafe_allow_html=True)
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
        "<p>Simulez la capitalisation trimestrielle ou semestrielle de votre épargne.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Vue d’ensemble du compte")
    c1, c2, c3, c4, c5 = st.columns(5)
    start_date = c1.date_input("Date", value=date.today())
    initial = c2.number_input("Capital initial (TND)", min_value=0.0, value=1000.0, step=100.0)
    compound_rate = c3.number_input("Taux d’intérêt (%)", min_value=0.0, value=5.0, step=0.25)
    duration = c4.number_input("Durée (années)", min_value=0.0, value=2.0, step=0.25)
    frequency = c5.selectbox("Capitalisation", ["Trimestrielle", "Semestrielle"])

    st.markdown("### Estimation de la capitalisation")
    try:
        if duration == 0:
            st.info("Saisissez une durée supérieure à zéro pour afficher l’estimation.")
        else:
            interest, final_capital, periodic_rate = compound_interest(
                initial, compound_rate, duration, frequency
            )
            m1, m2, m3 = st.columns(3)
            m1.metric("Intérêts générés", format_tnd(interest))
            m2.metric("Capital acquis", format_tnd(final_capital))
            m3.metric("Taux par période", f"{periodic_rate * Decimal('100'):.4f} %")

        with st.expander("Comprendre la capitalisation"):
            st.write(
                "Chaque trimestre ou semestre, les intérêts sont ajoutés au capital puis produisent à leur tour des intérêts. "
                "La formule utilisée est **Cₙ = C₀ × (1 + r/p)^(p×n)**, où r est le taux annuel, "
                "p le nombre de périodes par année et n la durée en années."
            )
    except ValueError as error:
        st.error(str(error))

    st.markdown("### Activité du compte")
    year = start_date.year
    operations_key = f"savings_operations_{year}"
    if operations_key not in st.session_state:
        st.session_state[operations_key] = []
    operations = st.session_state[operations_key]

    with st.form(f"add_operation_form_{year}", clear_on_submit=True):
        st.markdown("**Ajouter une opération**")
        op_date_col, op_type_col, amount_col, submit_col = st.columns([1.2, 1, 1, 0.8])
        operation_date = op_date_col.date_input(
            "Date de l’opération",
            value=start_date,
            min_value=date(year, 1, 1),
            max_value=date(year, 12, 31),
            key=f"new_operation_date_{year}",
        )
        operation_type = op_type_col.selectbox(
            "Type de mouvement", ["Versement", "Retrait"], key=f"new_operation_type_{year}"
        )
        amount = amount_col.number_input(
            "Montant (TND)", min_value=0.0, value=100.0, step=50.0,
            key=f"new_operation_amount_{year}",
        )
        submitted = submit_col.form_submit_button("Ajouter", type="primary", use_container_width=True)

    if submitted:
        operations.append((operation_date, operation_type, amount))
        st.session_state[operations_key] = operations
        st.success("Opération ajoutée au tableau.")

    if operations:
        st.markdown("#### Opérations enregistrées")
        operation_rows = [
            {
                "Date": op_date.strftime("%d/%m/%Y"),
                "Type": op_type,
                "Montant (TND)": float(money(op_amount)),
                "Date valeur": value_date(op_date, op_type).strftime("%d/%m/%Y"),
            }
            for op_date, op_type, op_amount in sorted(operations, key=lambda operation: (operation[0], operation[1]))
        ]
        st.dataframe(operation_rows, use_container_width=True, hide_index=True)
    else:
        st.markdown(
            "<div class='section-card'><b>Aucune opération enregistrée</b><br>"
            "<span class='small-note'>Ajoutez un versement ou un retrait avec le formulaire ci-dessus.</span></div>",
            unsafe_allow_html=True,
        )

    try:
        result = calculate_savings(initial, compound_rate, operations, year)
        st.markdown("### Synthèse annuelle")
        m1, m2, m3 = st.columns(3)
        m1.metric("Solde hors intérêts", format_tnd(result["balance"]))
        m2.metric("Intérêts estimés", format_tnd(result["interest"]))
        m3.metric("Capital acquis", format_tnd(result["capital"]))

        st.markdown("### Détail du calcul des intérêts")
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
    except ValueError as error:
        st.error(str(error))
