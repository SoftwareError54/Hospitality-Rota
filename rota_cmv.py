from itertools import combinations, product
from collections import defaultdict

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

def shift(weekday, kind):
    dur = 7
    return "{}_{}".format(weekday, kind), dur

# -----------------------
# Example Staff and Shift Lists
# Replace with your full data
# -----------------------

# -----------------------
# Greedy CSP Solver with Week-Aware Priority
# -----------------------
class RotaCSP:
    def __init__(self, staff_list, shift_list, debug=False):
        self.staff_list = staff_list
        self.shift_list = shift_list
        self.solution = None
        self.debug = debug

        # Define role tiers
        self.ROLE_TIERS = [
            ["manage_bbq"],       # BBQ first
            ["manager"],                     # Managers
            ["open_bar", "close_bar", "open_pool", "close_pool"],  # Openers/Closers
            ["bar", "floor"]                 # Everyone else
        ]

    def solve_greedy_priority(self):
        assignment = defaultdict(list)
        hours_per_staff = defaultdict(int)

        # Week and time order
        DAY_ORDER = ["Mon","Tue","Wed","Thur","Fri","Sat","Sun"]
        TIME_ORDER = ["Lunch","Evening"]

        # Sort shifts by week order
        sorted_shifts = sorted(self.shift_list, key=lambda s: (
            DAY_ORDER.index(s.shift_id.split("_")[0]),
            TIME_ORDER.index(s.shift_id.split("_")[1])
        ))

        # Assign by role tiers
        for tier in self.ROLE_TIERS:
            for shift in sorted_shifts:
                for role in tier:
                    if role not in shift.roles_required:
                        continue
                    count_needed = shift.roles_required[role]
                    assigned_count = sum(1 for s,r in assignment[shift.shift_id] if r==role)
                    remaining = count_needed - assigned_count
                    if remaining <= 0:
                        continue

                    # Eligible staff
                    eligible_staff = [s for s in self.staff_list
                                      if role in s.skills
                                      and shift.shift_id in s.availability
                                      and hours_per_staff[s.name] + shift.duration <= s.max_hours
                                      and s.name not in [st.name for st,r in assignment[shift.shift_id]]]

                    # Sort by min_hours descending
                    eligible_staff.sort(key=lambda s: -s.min_hours)

                    # Assign staff
                    for staff_member in eligible_staff[:remaining]:
                        assignment[shift.shift_id].append((staff_member, role))
                        hours_per_staff[staff_member.name] += shift.duration
                        if self.debug:
                            print("Assigned {} to '{}' in '{}' (hours: {})"
                                  .format(staff_member.name, role, shift.shift_id, hours_per_staff[staff_member.name]))

                    if remaining > len(eligible_staff) and self.debug:
                        print("Warning: Could not fill role '{}' in '{}' (assigned {}/{})"
                              .format(role, shift.shift_id, len(eligible_staff), remaining))

        # Fill any remaining unassigned roles with remaining staff
        for shift in sorted_shifts:
            for role, count in shift.roles_required.items():
                assigned_count = sum(1 for s,r in assignment[shift.shift_id] if r==role)
                remaining = count - assigned_count
                if remaining <= 0:
                    continue

                eligible_staff = [s for s in self.staff_list
                                  if role in s.skills
                                  and shift.shift_id in s.availability
                                  and hours_per_staff[s.name] + shift.duration <= s.max_hours
                                  and s.name not in [st.name for st,r in assignment[shift.shift_id]]]

                eligible_staff.sort(key=lambda s: -s.min_hours)
                for staff_member in eligible_staff[:remaining]:
                    assignment[shift.shift_id].append((staff_member, role))
                    hours_per_staff[staff_member.name] += shift.duration
                    if self.debug:
                        print("Assigned {} to '{}' in '{}' (hours: {})"
                              .format(staff_member.name, role, shift.shift_id, hours_per_staff[staff_member.name]))

        self.solution = assignment
        return assignment
# Example usage:

# Define staff
staff_list = [ Staff("Boss", {"Mon_Lunch","Mon_Evening","Wed_Lunch","Wed_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 32, 50, {"open_bar","close_bar","manager","bar","floor"}),
               Staff("Assistant Manager", {"Tue_Lunch","Tue_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 32, 50, {"open_bar","close_bar","close_pool","open_pool","manager","bar","floor"}),
               Staff("Senior", {}, 40,45, {"open_bar","close_bar","manager","bar","floor"}),
               Staff("Senior", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 40, {"open_bar","bar","floor"}),
               Staff("Senior", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 45, {"manage_bbq","close_bar","bar","floor"}),
               Staff("Senior", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 45, {"open_bar","close_bar","manage_bbq","bar","floor"}),
               Staff("Senior", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 35, 40, {"open_bar","close_bar","bar","floor"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","bar","floor"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 45, {"open_bar","close_bar","bar"}),
               Staff("Casual",{"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 40, 45, {"manage_bbq","floor"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","bar"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","bar", "floor"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","open_pool","close_pool","bar","floor"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"open_bar","close_bar","bar"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"floor"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 20, 40, {"floor","bar"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 20, 40, {"floor"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 12, 35, {"open_bar","close_bar","open_pool","bar", "floor"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 50, {"manage_bbq"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 50, {"floor","bar", "manager"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 40, {"floor", "bar"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 30, {"floor","young"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 30, {"floor","young"}),
               Staff("Casual",{"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 10, {"manager", "close_bar","floor"}),
               Staff("Casual", {"Mon_Lunch","Mon_Evening","Tue_Lunch","Tue_Evening","Wed_Lunch","Wed_Evening","Thur_Lunch","Thur_Evening","Fri_Lunch","Fri_Evening","Sat_Lunch","Sat_Evening","Sun_Lunch","Sun_Evening"}, 0, 10, {"manager", "bar", "close_bar", "floor"})
               ]

# Define shifts
shift_list = [
    # Mon
    ShiftSpec(*shift("Mon","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 1}),
    ShiftSpec(*shift("Mon","Evening"), {"manager":1,"close_bar":1, "bar": 1, "floor": 1}),
    # Tue
    ShiftSpec(*shift("Tue","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 1}),
    ShiftSpec(*shift("Tue","Evening"), {"manager":1,"close_bar":1, "bar": 1, "floor": 1}),
    # Wed
    ShiftSpec(*shift("Wed","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 1}),
    ShiftSpec(*shift("Wed","Evening"), {"manager":1,"close_bar":1, "bar": 1, "floor": 1}),
    # Thu (keep "Thur" to match your availability labels)
    ShiftSpec(*shift("Thur","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 1}),
    ShiftSpec(*shift("Thur","Evening"),{"manager":1,"close_bar":1, "bar": 1, "floor": 1}),
    # Fri
    ShiftSpec(*shift("Fri","Lunch"), {"manager":1,"open_bar":1, "bar": 1, "floor": 1}),
    ShiftSpec(*shift("Fri","Evening"), {"manager":1,"close_bar":1, "bar": 2, "floor": 1}),
    # Sat busier)
    ShiftSpec(*shift("Sat","Lunch"), {"manager":1,"open_bar":1, "bar": 3, "floor": 1}),
    ShiftSpec(*shift("Sat","Evening"), {"manager":1,"close_bar":1, "bar": 3, "floor": 1}),
    # Sun
    ShiftSpec(*shift("Sun","Lunch"), {"manager":1,"open_bar":1, "bar": 3, "floor": 2}),
    ShiftSpec(*shift("Sun","Evening"), {"manager":1,"close_bar":1, "bar": 2}), ]

# Solve
rota = RotaCSP(staff_list, shift_list, debug = True)
solution = rota.solve_greedy_priority()

DAY_ORDER = ["Mon", "Tue", "Wed", "Thur", "Fri", "Sat", "Sun"]
TIME_ORDER = ["Lunch", "Evening"]


sorted_solution = sorted(solution.items(),
                         key=lambda x: (
                             DAY_ORDER.index(x[0].split("_")[0]),
                             TIME_ORDER.index(x[0].split("_")[1])
                         ))

print("\n=== Final Rota (Day Order) ===")
for shift_id, roles in sorted_solution:
    print(shift_id, [(s.name, r) for s, r in roles])

