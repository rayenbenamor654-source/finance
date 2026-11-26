from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st


TND = Decimal("0.001")


def money(value):
    return Decimal(str(value)).quantize(TND, rounding=ROUND_HALF_UP)


def format_tnd(value):
    formatted = f"{money(value):,.3f}"
    return formatted.replace(" ", "").replace(",", " ").replace(".", ",") + " TND"


def simple_interest(capital, annual_rate_percent, duration, unit):
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


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def value_date(operation_date, operation_type):
    if operation_type not in ("Versement", "Retrait"):
        raise ValueError("Type d’opération invalide.")

    if operation_type == "Versement":
        if operation_date.day in (1, 16):
            return operation_date
        if operation_date.day < 16:
            return date(operation_date.year, operation_date.month, 16)
        return add_months(operation_date.replace(day=1), 1)

    if operation_date.day <= 15:
        return operation_date.replace(day=1)
    return date(operation_date.year, operation_date.month, 16)


def days_360(start, end):
    return (
        (end.year - start.year) * 360
        + (end.month - start.month) * 30
        + min(end.day, 30)
        - min(start.day, 30)
    )


def calculate_savings(initial_balance, annual_rate, operations, opening_date):
    balance = money(initial_balance)
    rate = Decimal(str(annual_rate))

    if balance < 0:
        raise ValueError("Le capital initial ne peut pas être négatif.")
    if rate <= 0:
        raise ValueError("Le taux annuel doit être supérieur à zéro.")

    frequency_months = 3
    end = add_months(opening_date, 12)
    valued_operations = []

    for operation_date, operation_type, amount in operations:
        amount = money(amount)
        if amount <= 0:
            raise ValueError("Le montant d’une opération doit être supérieur à zéro.")
        if not opening_date <= operation_date < end:
            continue

        effective_date = max(value_date(operation_date, operation_type), opening_date)
        if effective_date >= end:
            continue

        signed_amount = amount if operation_type == "Versement" else -amount
        valued_operations.append((effective_date, operation_date, operation_type, signed_amount))

    valued_operations.sort(key=lambda item: (item[0], item[1], item[2]))
    divisor = Decimal("360") / rate
    segments = []
    capitalizations = []
    operation_index = 0
    period_start = opening_date
    total_interest = Decimal("0")

    def apply_operation(operation):
        nonlocal balance
        effective_date, operation_date, _, signed_amount = operation
        balance = money(balance + signed_amount)
        if balance < 0:
            raise ValueError(
                f"Le retrait du {operation_date.strftime('%d/%m/%Y')} dépasse le solde disponible "
                f"à sa date de valeur ({effective_date.strftime('%d/%m/%Y')})."
            )

    while period_start < end:
        elapsed_months = (
            (period_start.year - opening_date.year) * 12
            + period_start.month - opening_date.month
        )
        period_end = min(
            add_months(opening_date, elapsed_months // frequency_months * frequency_months + frequency_months),
            end,
        )

        # Apply transactions effective on the first day before interest accrues.
        while operation_index < len(valued_operations) and valued_operations[operation_index][0] <= period_start:
            apply_operation(valued_operations[operation_index])
            operation_index += 1

        segment_start = period_start
        period_numbers = Decimal("0")

        while operation_index < len(valued_operations) and valued_operations[operation_index][0] < period_end:
            operation = valued_operations[operation_index]
            effective_date = operation[0]
            days = days_360(segment_start, effective_date)

            if days > 0:
                number = balance * Decimal(days) / Decimal("100")
                segments.append((segment_start, effective_date, balance, days, number))
                period_numbers += number

            segment_start = effective_date
            apply_operation(operation)
            operation_index += 1

        days = days_360(segment_start, period_end)
        if days > 0:
            number = balance * Decimal(days) / Decimal("100")
            segments.append((segment_start, period_end, balance, days, number))
            period_numbers += number

        credited_interest = money(period_numbers / divisor)
        balance = money(balance + credited_interest)
        total_interest += credited_interest
        capitalizations.append((period_end, credited_interest, balance))
        period_start = period_end

    return {
        "balance": balance,
        "interest": money(total_interest),
        "capital": balance,
        "segments": segments,
        "capitalizations": capitalizations,
        "end_date": end,
    }


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
        --ink: #20354a; --muted: #718096; --teal: #167c70; --teal-dark: #11675e;
        --canvas: #f2f0e9; --surface: #faf9f5; --line: #e4e0d5; --gold: #c49a53;
      }
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      .stApp { background: var(--canvas); color: var(--ink); }
      [data-testid="stHeader"] { background: rgba(242, 240, 233, .92); backdrop-filter: blur(10px); }
      [data-testid="stSidebar"] { background: #20384b; border-right: 1px solid #304a5c; }
      [data-testid="stSidebar"] * { color: #f2f0e9 !important; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c2d0d5 !important; }
      [data-testid="stSidebar"] hr { border-color: #496070; }
      h1, h2, h3 { font-family: 'Manrope', sans-serif; color: var(--ink); letter-spacing: -.035em; }
      .stMainBlockContainer { padding-top: 2rem; }
      .hero {
        position: relative; overflow: hidden; padding: 1.8rem 2rem; border-radius: 20px;
        margin: .15rem 0 1.7rem; color: #f7f5ef;
        background: linear-gradient(118deg, #20384b 0%, #27665f 100%);
        box-shadow: 0 14px 34px rgba(32, 56, 75, .13);
        animation: hero-enter .5s ease-out both;
      }
      .hero::after {
        content: ''; position: absolute; width: 230px; height: 230px; border-radius: 50%;
        right: -75px; top: -135px; border: 1px solid rgba(242,240,233,.17);
        box-shadow: 0 0 0 25px rgba(242,240,233,.035), 0 0 0 52px rgba(242,240,233,.025);
      }
      .hero h1 { color: #f7f5ef; margin: 0 0 .4rem; font-size: 2rem; }
      .hero p { color: #d7e2dc; margin: 0; }
      .eyebrow { text-transform: uppercase; letter-spacing: .15em; color: #d8bd83;
                 font-weight: 700; font-size: .72rem; margin-bottom: .5rem; }
      .section-card { background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
                      padding: 1.35rem 1.5rem; margin-bottom: 1rem; }
      .estimation-panel {
        background: linear-gradient(145deg, #faf9f5 0%, #edf5f2 100%);
        border: 1px solid #d7e4df; border-radius: 20px; padding: 1.35rem;
        box-shadow: 0 12px 28px rgba(32, 56, 75, .09);
      }
      .estimation-panel h3 { margin: 0 0 1rem; font-size: 1.25rem; }
      .estimation-panel [data-testid="stMetric"] { min-height: 118px; }
      [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; transition: box-shadow .2s ease, transform .2s ease; }
      [data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow: 0 10px 24px rgba(32,56,75,.08); transform: translateY(-1px); }
      [data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--line);
        border-radius: 15px; padding: 1.05rem 1.2rem; animation: metric-enter .45s ease both; }
      [data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
      [data-testid="stMetricValue"] { color: var(--teal); font-family: 'Manrope', sans-serif; font-size: 1.55rem; }
      div.stButton > button[kind="primary"] { background: var(--teal); border: 0; border-radius: 10px; }
      div.stButton > button[kind="primary"]:hover { background: var(--teal-dark); }
      .small-note { color: var(--muted); font-size: .87rem; }
      [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
      @keyframes hero-enter { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      @keyframes metric-enter { from { opacity: 0; transform: translateY(7px); } to { opacity: 1; transform: translateY(0); } }
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
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
    page = st.radio("Navigation", ["1 · Calcul d’intérêt", "2 · Compte d’épargne"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("Estimations indicatives · Consultez les conditions de votre établissement.")


if page == "1 · Calcul d’intérêt":
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 01</div>"
        "<h1>Calcul d’intérêt simple</h1>"
        "<p>Estimez la rémunération de votre capital, sans capitalisation des intérêts.</p></div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            capital = c1.number_input("Capital initial (TND)", min_value=0.0, value=0.0, step=100.0)
            annual_rate = c2.number_input("Taux annuel (%)", min_value=0.0, value=5.0, step=0.25)
            c3, c4 = st.columns(2)
            duration = c3.number_input("Durée", min_value=0.0, value=2.0, step=0.5)
            unit = c4.selectbox("Période", ["Années", "Mois", "Jours"])

    with right:
        if duration > 0:
            interest, final_capital, _ = simple_interest(capital, annual_rate, duration, unit)
            with st.container():
                st.markdown('<div class="estimation-panel">', unsafe_allow_html=True)
                st.markdown("### Votre estimation")
                st.metric("Intérêts estimés", format_tnd(interest))
                st.metric("Capital final", format_tnd(final_capital))
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Indiquez une durée supérieure à zéro pour afficher l’estimation.")

    with st.expander("À propos du calcul"):
        st.write(
            "Les intérêts simples sont calculés uniquement sur le capital initial et ne sont pas ajoutés au capital "
            "pendant la période choisie. Pour les durées en jours, le calcul utilise une année commerciale de 360 jours."
        )

else:
    st.markdown(
        "<div class='hero'><div class='eyebrow'>ESPACE FINANCE &nbsp; / &nbsp; 02</div>"
        "<h1>Compte d’épargne</h1>"
        "<p>Suivez vos versements et retraits, avec des intérêts capitalisés chaque trimestre.</p></div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    opening_date = c1.date_input("Date d’ouverture du compte", value=date.today())
    initial = c2.number_input("Capital initial (TND)", min_value=0.0, value=0.0, step=100.0)
    rate = c3.number_input("Taux annuel (%)", min_value=0.01, value=5.0, step=0.25)
    projection_end = add_months(opening_date, 12)
    st.caption(
        f"Projection du {opening_date.strftime('%d/%m/%Y')} au {projection_end.strftime('%d/%m/%Y')}. "
        "Les intérêts sont ajoutés au solde tous les trois mois."
    )

    st.markdown("### Opérations du compte")
    if "savings_operation_count" not in st.session_state:
        st.session_state.savings_operation_count = 0

    operation_count = st.session_state.savings_operation_count
    add_col, remove_col, _ = st.columns([1.2, 1.2, 3])
    if add_col.button("＋ Ajouter une opération", type="primary", use_container_width=True):
        st.session_state.savings_operation_count += 1
        st.rerun()
    if remove_col.button("− Supprimer la dernière", disabled=operation_count == 0, use_container_width=True):
        st.session_state.savings_operation_count = max(0, operation_count - 1)
        st.rerun()

    operations = []
    if operation_count == 0:
        st.markdown(
            "<div class='section-card'><b>Aucune opération pour le moment</b><br>"
            "<span class='small-note'>Ajoutez un versement ou un retrait pour l’inclure dans la projection.</span></div>",
            unsafe_allow_html=True,
        )

    for index in range(operation_count):
        with st.container(border=True):
            st.markdown(f"**Opération {index + 1:02d}**")
            cols = st.columns([1.2, 1, 1, 0.8])
            operation_date = cols[0].date_input(
                "Date de l’opération",
                value=opening_date,
                min_value=opening_date,
                max_value=projection_end,
                key=f"savings_date_{index}",
            )
            operation_type = cols[1].selectbox(
                "Type d’opération",
                ["Versement", "Retrait"],
                key=f"savings_type_{index}",
            )
            amount = cols[2].number_input(
                "Montant (TND)",
                min_value=0.001,
                value=100.0,
                step=50.0,
                key=f"savings_amount_{index}",
            )
            effective_date = max(value_date(operation_date, operation_type), opening_date)
            cols[3].caption(f"Date valeur : {effective_date.strftime('%d/%m/%Y')}")
            operations.append((operation_date, operation_type, amount))

    try:
        result = calculate_savings(initial, rate, operations, opening_date)
        st.markdown("### Synthèse après un an")
        m1, m2, m3 = st.columns(3)
        m1.metric("Capital initial", format_tnd(initial))
        m2.metric("Intérêts capitalisés", format_tnd(result["interest"]))
        m3.metric("Capital acquis", format_tnd(result["capital"]))

        st.markdown("### Échéances de capitalisation trimestrielle")
        capitalization_rows = [{
            "Échéance": when.strftime('%d/%m/%Y'),
            "Intérêts ajoutés (TND)": float(amount),
            "Solde après capitalisation (TND)": float(balance),
        } for when, amount, balance in result["capitalizations"]]
        if capitalization_rows:
            st.dataframe(capitalization_rows, use_container_width=True, hide_index=True)

        with st.expander("Voir le détail du calcul des intérêts"):
            rows = [{
                "Du": start.strftime('%d/%m/%Y'),
                "Au": end.strftime('%d/%m/%Y'),
                "Solde (TND)": float(balance),
                "Jours (30/360)": days,
                "Nombres": float(number),
            } for start, end, balance, days, number in result["segments"]]
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)

        with st.expander("Comprendre la méthode"):
            st.write(
                "Les versements prennent effet le 1er ou le 16 du mois selon leur date d’opération. "
                "Les retraits sont pris en compte au début de la quinzaine correspondante. Les intérêts sont "
                "calculés sur une année commerciale de 360 jours et ajoutés au solde tous les trois mois."
            )

    except ValueError as error:
        st.error(str(error))
