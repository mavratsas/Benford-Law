import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import math
import os
import logging
from scipy.stats import chisquare
from ttkthemes import ThemedTk
import numpy as np
from scipy import stats

# Set Matplotlib backend for Tkinter compatibility
matplotlib.use('TkAgg')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('benfords_law_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Function to create tooltips with proper memory management
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None

        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window:
            return

        x = self.widget.winfo_rootx() + self.widget.winfo_width()
        y = self.widget.winfo_rooty()

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background="yellow",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=2
        )
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

def create_tooltip(widget, text):
    """Factory function to create tooltips"""
    return Tooltip(widget, text)

def get_first_digit(num):
    """
    Extract the first non-zero digit from a number.
    Handles decimals, scientific notation, and negative numbers correctly.

    Args:
        num: numeric value

    Returns:
        int: first non-zero digit (1-9), or 0 if number is 0
    """
    try:
        num = abs(float(num))
        if num == 0:
            return 0

        # Normalize the number to get the first digit
        while num < 1:
            num *= 10
        while num >= 10:
            num /= 10

        return int(num)
    except (ValueError, TypeError):
        return 0

def sanitize_csv_value(value):
    """
    Sanitize values to prevent CSV injection attacks.

    Args:
        value: value to sanitize

    Returns:
        sanitized value
    """
    if isinstance(value, str):
        # Remove potentially dangerous characters that could trigger formulas
        if value.startswith(('=', '+', '-', '@', '\t', '\r')):
            return "'" + value
    return value

class BenfordsLawApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Benford's Law Analysis by Intelligent Synapse Ltd")
        self.root.geometry("900x700")

        logger.info("Benford's Law Application started")

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
        self.file_menu = file_menu

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
                logger.info(f"Loading file: {self.file_path}")
                if self.file_path.endswith('.csv'):
                    self.data = pd.read_csv(self.file_path)
                else:
                    self.data = pd.read_excel(self.file_path)

                logger.info(f"File loaded successfully. Shape: {self.data.shape}")
                self.status.set(f"Loaded file: {os.path.basename(self.file_path)}")
                self.preview_data()
                self.analyze_button.config(state=tk.NORMAL)
                self.save_button.config(state=tk.DISABLED)
                self.file_menu.entryconfig("Save Results", state=tk.DISABLED)
                self.results_preview.delete(1.0, tk.END)
            except Exception as e:
                logger.error(f"Failed to load file: {e}", exc_info=True)
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
                logger.warning("No numeric columns found in the data")
                messagebox.showerror("Error", "No numeric columns found in the data.")
                return

            column = self.select_column(numeric_cols)
            if column:
                logger.info(f"Analyzing column: {column}")
                data_series = self.data[column].dropna()

                # Log initial data statistics
                logger.info(f"Initial data count: {len(data_series)}")

                data_series = self.filter_data(data_series)
                if data_series.empty:
                    logger.warning("No data left after filtering")
                    messagebox.showwarning("No Data", "No data left after filtering.")
                    return

                # Extract first digits using improved method
                first_digits = data_series.apply(get_first_digit)

                # Filter out zeros and invalid digits
                first_digits = first_digits[(first_digits > 0) & (first_digits <= 9)]

                # Validate we have data after extraction
                if len(first_digits) == 0:
                    logger.warning("No valid first digits found after extraction")
                    messagebox.showwarning("No Data", "No valid first digits found in the data.")
                    return

                logger.info(f"Valid first digits count: {len(first_digits)}")

                # Count occurrences of each digit
                digit_counts = first_digits.value_counts().sort_index()

                # Ensure all digits 1-9 are represented (with 0 count if not present)
                digit_counts = digit_counts.reindex(range(1, 10), fill_value=0)

                total_counts = digit_counts.sum()

                # Validate total counts
                if total_counts == 0:
                    logger.warning("Total count is zero after processing")
                    messagebox.showwarning("No Data", "No valid data to analyze.")
                    return

                expected_counts = self.expected_probs * total_counts

                # Chi-squared Test
                try:
                    chi_stat, p_value = chisquare(digit_counts.values, expected_counts.values)
                    logger.info(f"Chi-squared test: statistic={chi_stat:.4f}, p-value={p_value:.4f}")
                except Exception as e:
                    logger.error(f"Chi-squared test failed: {e}", exc_info=True)
                    messagebox.showerror("Error", f"Statistical test failed:\n{e}")
                    return

                self.results = {
                    'Digit': list(range(1, 10)),
                    'Observed Counts': digit_counts.values.tolist(),
                    'Expected Counts': expected_counts.values.tolist(),
                    'Chi-squared Statistic': chi_stat,
                    'Chi-squared P-value': p_value,
                    'Column Analyzed': column,
                    'Total Data Points': int(total_counts)
                }

                self.show_results(column, chi_stat, p_value, total_counts)
                self.save_button.config(state=tk.NORMAL)
                self.file_menu.entryconfig("Save Results", state=tk.NORMAL)
                self.plot_results(digit_counts, expected_counts, column, chi_stat, p_value)
            else:
                logger.info("Column selection cancelled by user")
                messagebox.showwarning("Operation Cancelled", "No column selected.")
        else:
            logger.warning("Analyze called with no data loaded")
            messagebox.showerror("Error", "No data loaded.")

    def show_results(self, column, chi_stat, p_value, total_counts):
        self.results_preview.delete(1.0, tk.END)

        # Determine if data follows Benford's Law (typically p > 0.05 indicates conformance)
        conformance = "YES" if p_value > 0.05 else "NO"

        results_text = (
            f"Column Analyzed: {column}\n"
            f"Total Data Points: {int(total_counts)}\n"
            f"Chi-squared Statistic: {chi_stat:.2f}\n"
            f"Chi-squared P-value: {p_value:.4f}\n"
            f"Follows Benford's Law: {conformance} (p {'>' if p_value > 0.05 else '<'} 0.05)\n\n"
            f"{'Digit':<10}{'Observed':<15}{'Expected':<15}{'Difference':<15}\n"
            f"{'-'*55}\n"
        )
        for d, o, e in zip(self.results['Digit'], self.results['Observed Counts'], self.results['Expected Counts']):
            diff = o - e
            results_text += f"{d:<10}{o:<15}{e:<15.2f}{diff:<15.2f}\n"

        results_text += (
            f"\nInterpretation:\n"
            f"- A p-value > 0.05 suggests data follows Benford's Law\n"
            f"- A p-value < 0.05 suggests deviation from Benford's Law\n"
            f"- Lower p-values indicate stronger evidence of anomalies\n"
        )

        self.results_preview.insert(tk.END, results_text)
        logger.info(f"Results displayed for column: {column}")

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
        """Filter data by value range with improved state management"""
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

        # Use a mutable container to store the filtered data
        result = {'data': data_series}

        def apply_filter():
            min_val = min_entry.get()
            max_val = max_entry.get()
            try:
                filtered_data = data_series
                if min_val and max_val:
                    filtered_data = data_series[(data_series >= float(min_val)) & (data_series <= float(max_val))]
                    logger.info(f"Applied filter: {min_val} <= value <= {max_val}")
                elif min_val:
                    filtered_data = data_series[data_series >= float(min_val)]
                    logger.info(f"Applied filter: value >= {min_val}")
                elif max_val:
                    filtered_data = data_series[data_series <= float(max_val)]
                    logger.info(f"Applied filter: value <= {max_val}")
                else:
                    logger.info("No filter applied")

                result['data'] = filtered_data
                logger.info(f"Data after filtering: {len(filtered_data)} records")
                filter_window.destroy()
            except ValueError:
                logger.warning("Invalid filter input provided")
                messagebox.showerror("Invalid Input", "Please enter valid numeric values.")

        def cancel_filter():
            result['data'] = data_series
            logger.info("Filter cancelled")
            filter_window.destroy()

        apply_button = ttk.Button(filter_window, text="Apply Filter", command=apply_filter)
        apply_button.pack(pady=10)

        cancel_button = ttk.Button(filter_window, text="Cancel", command=cancel_filter)
        cancel_button.pack(pady=5)

        self.root.wait_window(filter_window)
        return result['data']

    def plot_results(self, digit_counts, expected_counts, column, chi_stat, p_value):
        digits = list(range(1, 10))
        observed = digit_counts.values.tolist()
        expected = expected_counts.values.tolist()

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

        # Add statistical information to the plot
        conformance = "YES" if p_value > 0.05 else "NO"
        textstr = f'Chi-squared Statistic: {chi_stat:.2f}\nP-value: {p_value:.4f}\nFollows Benford\'s Law: {conformance}'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=12, verticalalignment='top', bbox=props)

        plt.tight_layout()

        try:
            plt.show()
            logger.info("Plot displayed successfully")
        except Exception as e:
            logger.error(f"Failed to display plot: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to display plot:\n{e}")

    def save_results(self):
        if self.results:
            save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            if save_path:
                try:
                    df = pd.DataFrame({
                        'Digit': self.results['Digit'],
                        'Observed_Counts': self.results['Observed Counts'],
                        'Expected_Counts': self.results['Expected Counts'],
                        'Difference': [o - e for o, e in zip(self.results['Observed Counts'], self.results['Expected Counts'])]
                    })

                    # Sanitize column names to prevent CSV injection
                    df.columns = [sanitize_csv_value(col) for col in df.columns]

                    # Save with metadata
                    with open(save_path, 'w') as f:
                        f.write(f"# Benford's Law Analysis Results\n")
                        f.write(f"# Column Analyzed: {self.results['Column Analyzed']}\n")
                        f.write(f"# Total Data Points: {self.results['Total Data Points']}\n")
                        f.write(f"# Chi-squared Statistic: {self.results['Chi-squared Statistic']:.4f}\n")
                        f.write(f"# Chi-squared P-value: {self.results['Chi-squared P-value']:.4f}\n")
                        f.write(f"# Follows Benford's Law: {'YES' if self.results['Chi-squared P-value'] > 0.05 else 'NO'}\n#\n")
                        df.to_csv(f, index=False)

                    logger.info(f"Results saved to: {save_path}")
                    messagebox.showinfo("Success", "Results saved successfully.")
                except Exception as e:
                    logger.error(f"Failed to save results: {e}", exc_info=True)
                    messagebox.showerror("Error", f"Failed to save file:\n{e}")

    def show_help(self):
        help_text = (
            "Benford's Law Application Help\n\n"
            "1. Load a CSV or Excel file with numeric data using the 'Open File' button.\n"
            "2. After loading the data, select a numeric column to analyze.\n"
            "3. Optionally filter the data by specifying a value range.\n"
            "4. The application will perform Benford's Law analysis and show:\n"
            "   - Chi-squared test results\n"
            "   - Visual comparison of observed vs expected distributions\n"
            "   - Interpretation of results\n"
            "5. You can save the analysis results using the 'Save Results' button.\n\n"
            "Interpreting Results:\n"
            "- P-value > 0.05: Data likely follows Benford's Law (natural data)\n"
            "- P-value < 0.05: Data deviates from Benford's Law (potential anomalies)\n"
            "- The lower the p-value, the stronger the evidence of deviation\n\n"
            "Note: Benford's Law works best with naturally occurring datasets\n"
            "that span several orders of magnitude."
        )
        messagebox.showinfo("Help", help_text)

    def show_about(self):
        about_text = (
            "Benford's Law Analysis App\n"
            "Version 2.0\n\n"
            "Developed using Python and Tkinter\n"
            "by Intelligent Synapse Ltd\n\n"
            "This application analyzes numeric datasets to detect\n"
            "anomalies using Benford's Law statistical analysis."
        )
        messagebox.showinfo("About", about_text)

if __name__ == "__main__":
    try:
        logger.info("Starting Benford's Law Application")
        root = ThemedTk(theme="arc")
        app = BenfordsLawApp(root)
        root.mainloop()
        logger.info("Application closed normally")
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        raise
