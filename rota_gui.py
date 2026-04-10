import tkinter as tk
from tkinter import messagebox
import json
import os
from collections import defaultdict

from rota_cmv import RotaCSP, Staff, ShiftSpec, shift, shift_list, staff_list

SAVE_FILE = os.path.join(os.path.expanduser("~"),"availability.json")

class RotaApp:
    def __init__(self, root, staff_list, days, shift_types):
        self.root = root
        self.staff_names = [s.name for s in staff_list]
        self.days = days
        self.shift_types = shift_types
        self.check_vars = defaultdict(dict)
        self.staff_templates = {s.name: s for s in staff_list}

        self._build_ui()
        self._load_availability()

    def _build_ui(self):
        self.root.title("Bar Rota Generator")

        tk.Label(self.root, text="Staff", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        col = 1
        for d in self.days:
            for s in self.shift_types:
                tk.Label(self.root, text="{}\n{}".format(d, s), font=("Arial", 10)).grid(row=0, column=col, padx=2, pady=2)
                col += 1

        for i, staff in enumerate(self.staff_names):
            tk.Label(self.root, text=staff, font=("Arial", 10)).grid(row=i+1, column=0, sticky="w")
            col = 1
            for d in self.days:
                for s in self.shift_types:
                    shift_id = "{}_{}".format(d, s)
                    var = tk.IntVar()
                    tk.Checkbutton(self.root, variable=var).grid(row=i+1, column=col)
                    self.check_vars[staff][shift_id] = var
                    col += 1

        tk.Button(self.root, text="Save Availability", command=self._save_availability).grid(row=len(self.staff_names)+1, column=0, pady=10)
        tk.Button(self.root, text="Generate Rota", command=self._generate_rota).grid(row=len(self.staff_names)+1, column=1, pady=10)

    def _save_availability(self):
        data = {staff_name: [sid for sid, var in shift_map.items() if not var.get()]
                for staff_name, shift_map in self.check_vars.items()}
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Saved", "Availability saved to {}.".format(SAVE_FILE))

    def _load_availability(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    data = json.load(f)
                for staff_name, available_shifts in data.items():
                    if staff_name in self.check_vars:
                        for sid, var in self.check_vars[staff_name].items():
                            var.set(0 if sid in available_shifts else 1)
                messagebox.showinfo("Loaded", "Availability loaded from {}.".format(SAVE_FILE))
            except Exception as e:
                messagebox.showerror("Load Error", "Failed to load {}: {}".format(SAVE_FILE, e))

    def _generate_rota(self):
        staff_objs = []
        for name in self.staff_names:
            avail = [sid for sid, var in self.check_vars[name].items() if not var.get()]
            tmpl = self.staff_templates.get(name)
            if tmpl:
                staff_objs.append(Staff(name, avail, tmpl.min_hours, tmpl.max_hours, set(tmpl.skills)))
            else:
                staff_objs.append(Staff(name, avail, 0, 500, set(["bar","floor","open_bar","close_bar","manager"])))

        csp = RotaCSP(staff_objs, shift_list, debug=True)
        solution = csp.solve_greedy_priority()

        if not solution:
            messagebox.showerror("No Solution", "No valid rota found with current availability.")
            return

        by_shift = defaultdict(list)
        for shift_id, assignments in solution.items():
            for staff_member, role in assignments:
                by_shift[shift_id].append((role, staff_member.name))

        DAY_ORDER = ["Mon","Tue","Wed","Thur","Fri","Sat","Sun"]
        TIME_ORDER = ["Lunch","Evening"]

        lines = []
        for shift_id, assignments in sorted(by_shift.items(),
                                            key=lambda x: (
                                                DAY_ORDER.index(x[0].split("_")[0]),
                                                TIME_ORDER.index(x[0].split("_")[1])
                                            )):
            lines.append("{}:".format(shift_id))
            for role, who in sorted(assignments):
                lines.append("  {} -> {}".format(role, who))
            lines.append("")

        self._show_rota_window("\n".join(lines))

    def _show_rota_window(self, rota_str):
        window = tk.Toplevel(self.root)
        window.title("Generated Rota")
        text_frame = tk.Frame(window)
        text_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        text_widget = tk.Text(text_frame, wrap="none", yscrollcommand=scrollbar.set)
        text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
        text_widget.insert("1.0", rota_str)
        text_widget.config(state="disabled")

# -----------------------
# Run GUI
# -----------------------
if __name__ == "__main__":
    days = ["Mon", "Tue", "Wed", "Thur", "Fri", "Sat", "Sun"]
    shift_types = ["Lunch", "Evening"]

    root = tk.Tk()
    app = RotaApp(root, staff_list, days, shift_types)
    root.mainloop()

