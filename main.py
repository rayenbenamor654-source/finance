    st.markdown("### Ajouter une opération")
    last_operation_date = max(
        (operation[0] for operation in operations),
        default=start_date,
    )
    next_operation_date = max(start_date, last_operation_date + timedelta(days=1))

    with st.form("savings_operation_form", clear_on_submit=True):
        op1, op2, op3 = st.columns([1, 1, 1])
        operation_date = op1.date_input(
            "Date d’opération",
            value=max(next_operation_date, date.today()),
            min_value=next_operation_date,
        )
