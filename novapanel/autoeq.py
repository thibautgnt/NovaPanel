"""Egaliseur automatique selon l'application au premier plan."""


class AutoEq:
    """Applique la courbe associee a l'appli au premier plan, puis remet celle
    d'avant quand on la quitte.

    rules : [{"exe": "valorant.exe", "eq": "base:2" | "user:<nom>"}]
    """

    def __init__(self, apply_eq, ignored=()):
        self.apply_eq = apply_eq
        self.ignored = set(ignored)
        self.active = None
        self.saved = None

    def check(self, rules, current_target, app):
        if app is None:
            return
        rule = next((r for r in rules if r.get("exe", "").lower() == app), None)
        if rule and self.active != app:
            if self.active is None:
                self.saved = current_target
            self.active = app
            self.apply_eq(rule["eq"], app)
        elif not rule and self.active is not None and app not in self.ignored:
            # passer sur le bureau ou une fenetre systeme ne compte pas comme quitter l'appli
            self.active = None
            if self.saved:
                self.apply_eq(self.saved, None)
