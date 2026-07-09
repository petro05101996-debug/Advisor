def transition(state, event):
    if state == "CLOSED" and event == "PAY":
        raise DomainInvariantViolation("closed order cannot be paid")
