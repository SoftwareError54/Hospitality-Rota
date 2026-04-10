from collections import defaultdict

# -------------------------
# Data Models
# -------------------------

# Helper to define shift id and duration
def shift(weekday, kind):
    dur = 7  # duration of every shift (hours)
    return "{}_{}".format(weekday, kind), dur

class Staff:
    def __init__(self, name, availability, min_hours, max_hours, skills):
        self.name = name
        self.availability = set(availability)
        self.min_hours = min_hours
        self.max_hours = max_hours
        self.skills = set(skills)

class ShiftSpec:
    def __init__(self, shift_id, duration, roles_required):
        self.shift_id = shift_id
        self.duration = duration
        self.roles_required = dict(roles_required)

class Variable:
    def __init__(self, var_id, shift_id, role_required):
        self.var_id = var_id
        self.shift_id = shift_id
        self.role_required = role_required

# -------------------------
# CSP Solver
# -------------------------
class RotaCSP:
    def __init__(self, staff, shifts):
        self.staff = list(staff)
        self.staff_by_name = {s.name: s for s in self.staff}
        self.shifts = list(shifts)
        self.variables = self._build_variables()
        self.initial_domains = self._build_initial_domains()
        self.hours_assigned = defaultdict(int)
        self.assignment = {}
        self.calls = 0
        self.assignment_history = defaultdict(int)
        self.loop_limit = 10

    def _build_variables(self):
        variables = []
        for shift in self.shifts:
            for role, count in shift.roles_required.items():
                for i in range(count):
                    var_id = "{}__{}_{}".format(shift.shift_id, role, i+1)
                    variables.append(Variable(var_id, shift.shift_id, role))
        return variables

    def _build_initial_domains(self):
        domains = {}
        for var in self.variables:
            eligible = []
            for s in self.staff:
                if var.shift_id not in s.availability:
                    continue
                if var.role_required not in s.skills:
                    continue
                eligible.append(s.name)
            domains[var.var_id] = eligible
        return domains

    def _shift_by_id(self, sid):
        for sh in self.shifts:
            if sh.shift_id == sid:
                return sh
        raise KeyError(sid)

    def _var_by_id(self, var_id):
        for v in self.variables:
            if v.var_id == var_id:
                return v
        raise KeyError(var_id)

    # -------------------------
    # Variable selection
    # -------------------------
    def _select_unassigned_variable(self, domains):
        unassigned = [v for v in self.variables if v.var_id not in self.assignment]
        if not unassigned:
            return None

        # prioritize weekend/busy shifts first
        day_priority = {"Sat":0, "Sun":0, "Mon":1,"Tue":1,"Wed":1,"Thur":1,"Fri":1}
        def keyf(v):
            domain_size = len(self._current_domain(domains, v.var_id))
            day = v.shift_id.split("_")[0]
            return (day_priority.get(day, 2), domain_size)
        return min(unassigned, key=keyf).var_id

    # -------------------------
    # Domain filtering
    # -------------------------
    def _current_domain(self, domains, var_id):
        var = self._var_by_id(var_id)
        shift = self._shift_by_id(var.shift_id)
        out = []
        for staff_name in domains[var_id]:
            s = self.staff_by_name[staff_name]
            # reject if max_hours exceeded
            if self.hours_assigned[staff_name] + shift.duration > s.max_hours:
                continue
            # reject if already assigned in this shift
            if any(self.assignment.get(v2.var_id) == staff_name and v2.shift_id == var.shift_id
                   for v2 in self.variables):
                continue
            # check future feasibility
            if not self._can_satisfy_future(s, shift.duration):
                continue
            out.append(staff_name)
        return out

    def _can_satisfy_future(self, staff, additional_hours):
        remaining_hours = staff.max_hours - self.hours_assigned[staff.name] - additional_hours
        # sum hours required in remaining eligible shifts
        needed = 0
        for v in self.variables:
            if v.var_id in self.assignment:
                continue
            if staff.name in self.initial_domains[v.var_id]:
                shift = self._shift_by_id(v.shift_id)
                needed += shift.duration
        return remaining_hours >= 0 or remaining_hours >= needed

    # -------------------------
    # Assignment
    # -------------------------
    def _assign(self, var_id, staff_name):
        self.assignment[var_id] = staff_name
        shift = self._shift_by_id(self._var_by_id(var_id).shift_id)
        self.hours_assigned[staff_name] += shift.duration
        print("Assign: {} -> {} (hours assigned: {})".format(staff_name, var_id, self.hours_assigned[staff_name]))

    def _unassign(self, var_id):
        staff_name = self.assignment[var_id]
        shift = self._shift_by_id(self._var_by_id(var_id).shift_id)
        del self.assignment[var_id]
        self.hours_assigned[staff_name] -= shift.duration
        print("Unassign: {} <- {} (hours assigned: {})".format(staff_name, var_id, self.hours_assigned[staff_name]))

    # -------------------------
    # Forward checking
    # -------------------------
    def _forward_check(self, domains, var_id, staff_name):
        pruned = {k:list(v) for k,v in domains.items()}
        for v in self.variables:
            if v.var_id in self.assignment:
                continue
            if v.shift_id == self._var_by_id(var_id).shift_id and staff_name in pruned[v.var_id]:
                pruned[v.var_id].remove(staff_name)
            # reject if max_hours exceeded
            for sname in list(pruned[v.var_id]):
                s = self.staff_by_name[sname]
                sh = self._shift_by_id(v.shift_id)
                if self.hours_assigned[sname] + sh.duration > s.max_hours:
                    pruned[v.var_id].remove(sname)
            if len(self._current_domain(pruned, v.var_id)) == 0:
                return None
        return pruned

    # -------------------------
    # CSP core
    # -------------------------
    def _all_assigned(self):
        return len(self.assignment) == len(self.variables)

    def solve(self):
        domains = {k:list(v) for k,v in self.initial_domains.items()}
        return self._backtrack(domains)

    def _backtrack(self, domains):
        self.calls += 1
        if self._all_assigned():
            return dict(self.assignment)

        var_id = self._select_unassigned_variable(domains)
        if var_id is None:
            return None

        # detect repeated partial assignments
        state_hash = tuple(sorted(self.assignment.items()))
        self.assignment_history[state_hash] += 1
        if self.assignment_history[state_hash] > self.loop_limit:
            print("\n--- Loop limit reached ---")
            print("Current partial assignment:")
            for k,v in sorted(self.assignment.items()):
                print("  {} -> {}".format(k,v))
            return None

        # Least-Constraining-Value ordering
        candidates = sorted(self._current_domain(domains, var_id),
                            key=lambda s: -self._count_remaining_options(domains, s))
        for staff_name in candidates:
            self._assign(var_id, staff_name)
            pruned = self._forward_check(domains, var_id, staff_name)
            if pruned is not None:
                result = self._backtrack(pruned)
                if result is not None:
                    return result
            self._unassign(var_id)
        return None

    def _count_remaining_options(self, domains, staff_name):
        count = 0
        for v in self.variables:
            if v.var_id in self.assignment:
                continue
            if staff_name in domains[v.var_id]:
                count += 1
        return count

# -------------------------
# Data: Staff and Shift, initial hard coded full availability, skills and contract details hard coded for testing.
# -------------------------
staff = [ Staff("Boss", {"Mon_Lunch","Mon_Evening","Wed_Lunch","Wed_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 50, {"open_bar","close_bar","manager","bar","floor"}),
          Staff("Assistant Manager", {"Tue_Lunch","Tue_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 10, 50, {"open_bar","close_bar","close_pool","open_pool","manager","bar","floor"}),
          Staff("Senior", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 45, {"open_bbq","close_bbq","open_bar","close_bar","bar","floor"}),
          Staff("Senior", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 45, {"open_bar","close_bar","open_bbq","close_bbq","bar","floor"}),
          Staff("Senior", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 35, 40, {"open_bar","close_bar","bar","floor"}),
          Staff("Senior", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 35, 40, {"open_bar","close_bar","bar","floor"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","bar","floor"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 45, {"open_bar","close_bar","bar"}),
          Staff("Casual",{"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 45, {"open_bbq","close_bbq","floor"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","bar"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","bar"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","open_pool","close_pool","bar","floor"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","bar"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"floor"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 20, 40, {"floor","bar"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 20, 40, {"floor"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 35, {"open_bar","close_bar","open_pool","bar"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 50, {"open_bbq","close_bbq"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 50, {"floor","bar", "manager"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"floor", "bar"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 20, {"floor","young"}),
          Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 20, {"floor","young"}), ]




# -------------------------
# Shift template, requirements for each shift
# -------------------------
shifts = [
    # Mon
    ShiftSpec(*shift("Mon","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 1}),
    ShiftSpec(*shift("Mon","Evening"), {"manager":1,"close_bar":1, "bar": 2, "floor": 1}),
    # Tue
    ShiftSpec(*shift("Tue","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 1}),
    ShiftSpec(*shift("Tue","Evening"), {"manager":1,"close_bar":1, "bar": 2, "floor": 1}),
    # Wed
    ShiftSpec(*shift("Wed","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 2}),
    ShiftSpec(*shift("Wed","Evening"), {"manager":1,"close_bar":1, "bar": 2, "floor": 1}),
    # Thu (keep "Thur" to match your availability labels)
    ShiftSpec(*shift("Thur","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 1}),
    ShiftSpec(*shift("Thur","Evening"),{"manager":1,"close_bar":1, "bar": 2, "floor": 1}),
    # Fri
    ShiftSpec(*shift("Fri","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 2}),
    ShiftSpec(*shift("Fri","Evening"), {"manager":1,"close_bar":1, "bar": 2, "floor": 1}),
    # Sat busier)
    ShiftSpec(*shift("Sat","Lunch"), {"manager":1,"open_bar":1, "bar": 4, "floor": 2}),
    ShiftSpec(*shift("Sat","Evening"), {"manager":1,"close_bar":1, "bar": 4, "floor": 2}),
    # Sun
    ShiftSpec(*shift("Sun","Lunch"), {"manager":1,"open_bar":1, "bar": 4, "floor": 2}),
    ShiftSpec(*shift("Sun","Evening"), {"manager":1,"close_bar":1, "bar": 1, "floor": 1}), ]
# -------------------------
# Run
# -------------------------
def main():
    csp = RotaCSP(staff, shifts)
    solution = csp.solve()

    if solution is None:
        print("No valid rota found.")
        return

    print("Rota found!\n")
    by_shift = defaultdict(list)
    for var_id, who in solution.items():
        shift_id = var_id.split("__")[0]
        role = var_id.split("__")[1]
        by_shift[shift_id].append((role, who))

    for shift_id in sorted(by_shift.keys()):
        print("Shift: {}".format(shift_id))
        for role, who in sorted(by_shift[shift_id]):
            print("  {:12} -> {}".format(role, who))
        print()

    print("Hours assigned:")
    for name, hrs in sorted(csp.hours_assigned.items()):
        st = csp.staff_by_name[name]
        print("  {:10}: {} (max {})".format(name, hrs, st.max_hours))

if __name__ == "__main__":
    main()
