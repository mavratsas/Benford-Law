import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import math
import os
from scipy.stats import chisquare, kstest
from ttkthemes import ThemedTk
import numpy as np
from scipy import stats

# Set Matplotlib backend for Tkinter compatibility
matplotlib.use('TkAgg')

# Function to create tooltips
def create_tooltip(widget, text):
    tooltip = tk.Label(widget, text=text, background="yellow", relief="solid", borderwidth=1)
    tooltip.pack_forget()

    def enter(event):
        tooltip.place(x=widget.winfo_x() + widget.winfo_width(), y=widget.winfo_y())

    def leave(event):
        tooltip.place_forget()

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)

class BenfordsLawApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Benford's Law Analysis by Intelligent Synapse Ltd")
        self.root.geometry("900x700")

        # Create menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self.load_file)
        file_menu.add_command(label="Save Results", command=self.save_results, state=tk.DISABLED)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Help", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.open_button = ttk.Button(toolbar, text="Open File", command=self.load_file)
        self.open_button.pack(side=tk.LEFT, padx=4, pady=4)
        create_tooltip(self.open_button, "Click to open a CSV or Excel file.")

        self.analyze_button = ttk.Button(toolbar, text="Analyze", command=self.analyze_data, state=tk.DISABLED)
        self.analyze_button.pack(side=tk.LEFT, padx=4, pady=4)
        create_tooltip(self.analyze_button, "Analyze the loaded data for Benford's Law compliance.")

        self.save_button = ttk.Button(toolbar, text="Save Results", command=self.save_results, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=4, pady=4)
        create_tooltip(self.save_button, "Save the analysis results.")

        # Status bar
        self.status = tk.StringVar()
        self.status.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status, relief=tk.SUNKEN, anchor='w')
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Main content area
        self.content_frame = ttk.Frame(self.root, padding=10)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Data Preview
        preview_label = ttk.Label(self.content_frame, text="Data Preview (First 10 Rows):")
        preview_label.pack(anchor='w')
        self.data_preview = tk.Text(self.content_frame, wrap=tk.NONE, height=10)
        self.data_preview.pack(fill=tk.BOTH, expand=True, pady=5)

        # Analysis Results
        results_label = ttk.Label(self.content_frame, text="Analysis Results:")
        results_label.pack(anchor='w')
        self.results_preview = tk.Text(self.content_frame, wrap=tk.NONE, height=10)
        self.results_preview.pack(fill=tk.BOTH, expand=True, pady=5)

        self.file_path = None
        self.data = None
        self.results = None
        self.expected_probs = pd.Series([math.log10(1 + 1/d) for d in range(1, 10)], index=range(1, 10))

    def load_file(self):
        file_types = [("CSV Files", "*.csv"), ("Excel Files", "*.xlsx *.xls")]
        self.file_path = filedialog.askopenfilename(title="Select a CSV or Excel File", filetypes=file_types)
        if self.file_path:
            try:
                if self.file_path.endswith('.csv'):
                    self.data = pd.read_csv(self.file_path)
                else:
                    self.data = pd.read_excel(self.file_path)
                self.status.set(f"Loaded file: {os.path.basename(self.file_path)}")
                self.preview_data()
                self.analyze_button.config(state=tk.NORMAL)
                self.save_button.config(state=tk.DISABLED)
                self.results_preview.delete(1.0, tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{e}")
                self.status.set("Failed to load file.")
                self.analyze_button.config(state=tk.DISABLED)

    def preview_data(self):
        self.data_preview.delete(1.0, tk.END)
        if self.data is not None:
            preview = self.data.head(10).to_string(index=False)
            self.data_preview.insert(tk.END, preview)

    def analyze_data(self):
        if self.data is not None:
            numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()
            if not numeric_cols:
                messagebox.showerror("Error", "No numeric columns found in the data.")
                return
            column = self.select_column(numeric_cols)
            if column:
                data_series = self.data[column].dropna()
                data_series = self.filter_data(data_series)
                if data_series.empty:
                    messagebox.showwarning("No Data", "No data left after filtering.")
                    return

                # Optimize first digit extraction
                first_digits = data_series.abs().astype(str).str[0].astype(int)
                first_digits = first_digits[first_digits > 0]

                digit_counts = first_digits.value_counts().sort_index()
                total_counts = digit_counts.sum()

                expected_counts = self.expected_probs * total_counts

                # Chi-squared Test
                chi_stat, p_value = stats.chisquare(digit_counts.values, expected_counts)

                # Kolmogorov-Smirnov Test
                ks_stat, ks_p_value = stats.kstest(first_digits, stats.uniform(loc=1, scale=9).cdf)

                self.results = {
                    'Digit': list(range(1, 10)),
                    'Observed Counts': digit_counts.values.tolist(),
                    'Expected Counts': expected_counts.tolist(),
                    'Chi-squared Statistic': chi_stat,
                    'Chi-squared P-value': p_value,
                    'K-S Statistic': ks_stat,
                    'K-S P-value': ks_p_value,
                    'Column Analyzed': column
                }

                self.show_results(column, chi_stat, p_value, ks_stat, ks_p_value)
                self.save_button.config(state=tk.NORMAL)
                self.plot_results(digit_counts, expected_counts, column, chi_stat, p_value)
            else:
                messagebox.showwarning("Operation Cancelled", "No column selected.")
        else:
            messagebox.showerror("Error", "No data loaded.")

    def show_results(self, column, chi_stat, p_value, ks_stat, ks_p_value):
        self.results_preview.delete(1.0, tk.END)
        results_text = (
            f"Column Analyzed: {column}\n"
            f"Chi-squared Statistic: {chi_stat:.2f}\n"
            f"Chi-squared P-value: {p_value:.4f}\n"
            f"K-S Statistic: {ks_stat:.4f}\n"
            f"K-S P-value: {ks_p_value:.4f}\n\n"
            f"{'Digit':<10}{'Observed':<15}{'Expected':<15}\n"
            f"{'-'*40}\n"
        )
        for d, o, e in zip(self.results['Digit'], self.results['Observed Counts'], self.results['Expected Counts']):
            results_text += f"{d:<10}{o:<15}{e:<15.2f}\n"
        self.results_preview.insert(tk.END, results_text)

    def select_column(self, columns):
        selection_window = tk.Toplevel(self.root)
        selection_window.title("Select Column")
        selection_window.geometry("300x250")
        selection_window.grab_set()

        label = ttk.Label(selection_window, text="Select a numeric column for analysis:")
        label.pack(pady=10)

        listbox = tk.Listbox(selection_window, selectmode=tk.SINGLE, height=8)
        for col in columns:
            listbox.insert(tk.END, col)
        listbox.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        selected_column = tk.StringVar()

        def confirm_selection():
            selected = listbox.curselection()
            if selected:
                selected_column.set(listbox.get(selected))
                selection_window.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select a column to analyze.")

        confirm_button = ttk.Button(selection_window, text="Confirm", command=confirm_selection)
        confirm_button.pack(pady=10)

        self.root.wait_window(selection_window)
        return selected_column.get()

    def filter_data(self, data_series):
        filter_window = tk.Toplevel(self.root)
        filter_window.title("Filter Data")
        filter_window.geometry("300x200")
        filter_window.grab_set()

        label = ttk.Label(filter_window, text="Optional: Filter data by value range")
        label.pack(pady=10)

        min_label = ttk.Label(filter_window, text="Minimum Value:")
        min_label.pack(pady=5)
        min_entry = ttk.Entry(filter_window)
        min_entry.pack(pady=5)

        max_label = ttk.Label(filter_window, text="Maximum Value:")
        max_label.pack(pady=5)
        max_entry = ttk.Entry(filter_window)
        max_entry.pack(pady=5)

        def apply_filter():
            min_val = min_entry.get()
            max_val = max_entry.get()
            try:
                if min_val and max_val:
                    filtered_data = data_series[(data_series >= float(min_val)) & (data_series <= float(max_val))]
                elif min_val:
                    filtered_data = data_series[data_series >= float(min_val)]
                elif max_val:
                    filtered_data = data_series[data_series <= float(max_val)]
                else:
                    filtered_data = data_series
                filter_window.destroy()
                self.filtered_data = filtered_data
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numeric values.")

        apply_button = ttk.Button(filter_window, text="Apply Filter", command=apply_filter)
        apply_button.pack(pady=10)

        cancel_button = ttk.Button(filter_window, text="Cancel", command=lambda: setattr(self, 'filtered_data', data_series) or filter_window.destroy())
        cancel_button.pack(pady=5)

        self.root.wait_window(filter_window)
        return getattr(self, 'filtered_data', data_series)

    def plot_results(self, digit_counts, expected_counts, column, chi_stat, p_value):
        digits = list(range(1, 10))
        observed = digit_counts.values.tolist()
        expected = expected_counts.tolist()

        fig, ax = plt.subplots(figsize=(10, 6))

        bar_width = 0.35
        index = digits

        bars1 = ax.bar([i - bar_width / 2 for i in index], observed, bar_width, label='Observed', color='skyblue')
        bars2 = ax.bar([i + bar_width / 2 for i in index], expected, bar_width, label='Expected', color='salmon')

        ax.set_xlabel('Leading Digit')
        ax.set_ylabel('Frequency')
        ax.set_title(f"Benford's Law Analysis of '{column}'")
        ax.set_xticks(index)
        ax.set_xticklabels(digits)
        ax.legend()

        textstr = f'Chi-squared Statistic: {chi_stat:.2f}\nP-value: {p_value:.4f}'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=12, verticalalignment='top', bbox=props)

        plt.tight_layout()
        plt.show()  # Ensure the plot is displayed

    def save_results(self):
        if self.results:
            save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            if save_path:
                try:
                    df = pd.DataFrame({
                        'Digit': self.results['Digit'],
                        'Observed Counts': self.results['Observed Counts'],
                        'Expected Counts': self.results['Expected Counts']
                    })
                    df.to_csv(save_path, index=False)
                    messagebox.showinfo("Success", "Results saved successfully.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save file:\n{e}")

    def show_help(self):
        help_text = (
            "Benford's Law Application Help\n\n"
            "1. Load a CSV or Excel file with numeric data using the 'Open File' button.\n"
            "2. After loading the data, select a numeric column to analyze.\n"
            "3. The application will perform Benford's Law analysis and show the results.\n"
            "4. You can save the analysis results using the 'Save Results' button."
        )
        messagebox.showinfo("Help", help_text)

    def show_about(self):
        about_text = "Benford's Law Analysis App\nVersion 1.0\nDeveloped using Python and Tkinter."
        messagebox.showinfo("About", about_text)

if __name__ == "__main__":
    root = ThemedTk(theme="arc")
    app = BenfordsLawApp(root)
    root.mainloop()
