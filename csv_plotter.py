#!/usr/bin/env python3
"""
CSV Plotter GUI Application

A Python GUI application that allows users to:
- Load one or more CSV files
- Merge CSV files with various options
- Configure plot styles and column selections
- View real-time plot updates
- Save plots as PNG or SVG
"""

import sys
from typing import Optional
from pathlib import Path

import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox, QLineEdit,
    QSplitter, QScrollArea, QFrame, QDoubleSpinBox, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


class DataManager:
    """Manages loaded CSV data and merging operations."""

    def __init__(self):
        self.dataframes: dict[str, pd.DataFrame] = {}
        self.merged_data: Optional[pd.DataFrame] = None

    def load_csv(self, filepath: str) -> tuple[bool, str]:
        """Load a CSV file and store it with a unique name."""
        try:
            df = pd.read_csv(filepath)
            filename = Path(filepath).name
            # Ensure unique name
            base_name = filename
            counter = 1
            while filename in self.dataframes:
                filename = f"{base_name}_{counter}"
                counter += 1
            self.dataframes[filename] = df
            return True, filename
        except Exception as e:
            return False, str(e)

    def remove_csv(self, name: str) -> bool:
        """Remove a loaded CSV file."""
        if name in self.dataframes:
            del self.dataframes[name]
            return True
        return False

    def get_columns(self, name: str) -> list[str]:
        """Get column names for a specific dataframe."""
        if name in self.dataframes:
            return list(self.dataframes[name].columns)
        return []

    def get_all_columns(self) -> list[str]:
        """Get all unique column names across all dataframes."""
        columns = set()
        for df in self.dataframes.values():
            columns.update(df.columns)
        return sorted(list(columns))

    def merge_data(self, merge_type: str, merge_on: Optional[str] = None) -> tuple[bool, str]:
        """Merge all loaded dataframes based on the merge type."""
        if not self.dataframes:
            return False, "No data loaded"

        if len(self.dataframes) == 1:
            self.merged_data = list(self.dataframes.values())[0].copy()
            return True, "Single file loaded, no merge needed"

        try:
            dfs = list(self.dataframes.values())

            if merge_type == "Concatenate (Stack Rows)":
                self.merged_data = pd.concat(dfs, ignore_index=True)
            elif merge_type == "Concatenate (Side by Side)":
                self.merged_data = pd.concat(dfs, axis=1)
            elif merge_type == "Inner Join" and merge_on:
                result = dfs[0]
                for df in dfs[1:]:
                    if merge_on in result.columns and merge_on in df.columns:
                        result = result.merge(df, on=merge_on, how="inner")
                self.merged_data = result
            elif merge_type == "Outer Join" and merge_on:
                result = dfs[0]
                for df in dfs[1:]:
                    if merge_on in result.columns and merge_on in df.columns:
                        result = result.merge(df, on=merge_on, how="outer")
                self.merged_data = result
            elif merge_type == "Left Join" and merge_on:
                result = dfs[0]
                for df in dfs[1:]:
                    if merge_on in result.columns and merge_on in df.columns:
                        result = result.merge(df, on=merge_on, how="left")
                self.merged_data = result
            else:
                return False, "Invalid merge type or missing merge column"

            return True, f"Merged {len(dfs)} files successfully"
        except Exception as e:
            return False, str(e)

    def get_merged_columns(self) -> list[str]:
        """Get columns from merged data."""
        if self.merged_data is not None:
            return list(self.merged_data.columns)
        return []

    def get_numeric_columns(self) -> list[str]:
        """Get numeric columns from merged data."""
        if self.merged_data is not None:
            return list(self.merged_data.select_dtypes(include=[np.number]).columns)
        return []


class PlotCanvas(FigureCanvas):
    """Matplotlib canvas for rendering plots."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

    def clear_plot(self):
        """Clear the current plot."""
        self.axes.clear()
        self.fig.tight_layout()
        self.draw()

    def update_plot(self, data: Optional[pd.DataFrame], config: dict):
        """Update the plot with new data and configuration."""
        self.axes.clear()

        if data is None or data.empty:
            self.axes.text(
                0.5, 0.5, "No data to display",
                ha='center', va='center', transform=self.axes.transAxes
            )
            self.draw()
            return

        plot_type = config.get("plot_type", "Line")
        x_column = config.get("x_column")
        y_columns = config.get("y_columns", [])
        title = config.get("title", "")
        xlabel = config.get("xlabel", "")
        ylabel = config.get("ylabel", "")
        grid = config.get("grid", True)
        legend = config.get("legend", True)
        marker = config.get("marker", "")
        line_style = config.get("line_style", "-")
        alpha = config.get("alpha", 1.0)

        try:
            if not y_columns:
                self.axes.text(
                    0.5, 0.5, "Please select Y column(s)",
                    ha='center', va='center', transform=self.axes.transAxes
                )
                self.draw()
                return

            # Get X data
            if x_column and x_column in data.columns:
                x_data = data[x_column]
            else:
                x_data = data.index

            # Plot based on type
            for y_col in y_columns:
                if y_col not in data.columns:
                    continue
                y_data = data[y_col]

                if plot_type == "Line":
                    self.axes.plot(
                        x_data, y_data, marker=marker or None,
                        linestyle=line_style, alpha=alpha, label=y_col
                    )
                elif plot_type == "Scatter":
                    self.axes.scatter(x_data, y_data, alpha=alpha, label=y_col)
                elif plot_type == "Bar":
                    # For bar plots, limit data points
                    max_bars = 50
                    if len(x_data) > max_bars:
                        x_data = x_data[:max_bars]
                        y_data = y_data[:max_bars]
                    width = 0.8 / len(y_columns)
                    self.axes.bar(
                        range(len(x_data)), y_data, width=width,
                        alpha=alpha, label=y_col
                    )
                    if y_col == y_columns[0]:
                        self.axes.set_xticks(range(len(x_data)))
                        self.axes.set_xticklabels(
                            [str(x)[:10] for x in x_data],
                            rotation=45, ha='right'
                        )
                elif plot_type == "Histogram":
                    self.axes.hist(y_data.dropna(), bins=30, alpha=alpha, label=y_col)
                elif plot_type == "Area":
                    self.axes.fill_between(
                        range(len(y_data)), y_data, alpha=alpha, label=y_col
                    )
                elif plot_type == "Box":
                    # For box plots, collect all y data
                    pass

            if plot_type == "Box":
                box_data = [data[col].dropna() for col in y_columns if col in data.columns]
                if box_data:
                    self.axes.boxplot(box_data, tick_labels=y_columns)

            # Apply formatting
            if title:
                self.axes.set_title(title)
            if xlabel:
                self.axes.set_xlabel(xlabel)
            if ylabel:
                self.axes.set_ylabel(ylabel)
            if grid:
                self.axes.grid(True, alpha=0.3)
            if legend and plot_type != "Box":
                self.axes.legend()

            self.fig.tight_layout()
            self.draw()

        except Exception as e:
            self.axes.text(
                0.5, 0.5, f"Error: {str(e)}",
                ha='center', va='center', transform=self.axes.transAxes,
                color='red'
            )
            self.draw()

    def save_plot(self, filepath: str, dpi: int = 150):
        """Save the current plot to a file."""
        self.fig.savefig(filepath, dpi=dpi, bbox_inches='tight')


class FilePanel(QWidget):
    """Panel for loading and managing CSV files."""

    files_changed = pyqtSignal()

    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.data_manager = data_manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # File list
        file_group = QGroupBox("Loaded Files")
        file_layout = QVBoxLayout(file_group)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        file_layout.addWidget(self.file_list)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Files")
        self.add_btn.clicked.connect(self.add_files)
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_files)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        file_layout.addLayout(btn_layout)

        layout.addWidget(file_group)

        # Merge options
        merge_group = QGroupBox("Merge Options")
        merge_layout = QVBoxLayout(merge_group)

        merge_type_layout = QHBoxLayout()
        merge_type_layout.addWidget(QLabel("Merge Type:"))
        self.merge_type_combo = QComboBox()
        self.merge_type_combo.addItems([
            "Concatenate (Stack Rows)",
            "Concatenate (Side by Side)",
            "Inner Join",
            "Outer Join",
            "Left Join"
        ])
        self.merge_type_combo.currentTextChanged.connect(self.on_merge_type_changed)
        merge_type_layout.addWidget(self.merge_type_combo)
        merge_layout.addLayout(merge_type_layout)

        merge_on_layout = QHBoxLayout()
        merge_on_layout.addWidget(QLabel("Merge On:"))
        self.merge_on_combo = QComboBox()
        self.merge_on_combo.setEnabled(False)
        merge_on_layout.addWidget(self.merge_on_combo)
        merge_layout.addLayout(merge_on_layout)

        self.merge_btn = QPushButton("Apply Merge")
        self.merge_btn.clicked.connect(self.apply_merge)
        merge_layout.addWidget(self.merge_btn)

        layout.addWidget(merge_group)

        # Data preview info
        self.info_label = QLabel("No data loaded")
        layout.addWidget(self.info_label)

        layout.addStretch()

    def add_files(self):
        """Open file dialog to add CSV files."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select CSV Files", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        for filepath in files:
            success, result = self.data_manager.load_csv(filepath)
            if success:
                self.file_list.addItem(result)
            else:
                QMessageBox.warning(self, "Error", f"Failed to load {filepath}: {result}")

        if files:
            self.update_merge_columns()
            self.files_changed.emit()

    def remove_files(self):
        """Remove selected files."""
        for item in self.file_list.selectedItems():
            self.data_manager.remove_csv(item.text())
            self.file_list.takeItem(self.file_list.row(item))

        self.update_merge_columns()
        self.files_changed.emit()

    def on_merge_type_changed(self, merge_type: str):
        """Handle merge type change."""
        needs_column = merge_type in ["Inner Join", "Outer Join", "Left Join"]
        self.merge_on_combo.setEnabled(needs_column)

    def update_merge_columns(self):
        """Update the merge column combo box."""
        self.merge_on_combo.clear()
        columns = self.data_manager.get_all_columns()
        self.merge_on_combo.addItems(columns)

    def apply_merge(self):
        """Apply the selected merge operation."""
        merge_type = self.merge_type_combo.currentText()
        merge_on = self.merge_on_combo.currentText() if self.merge_on_combo.isEnabled() else None

        success, message = self.data_manager.merge_data(merge_type, merge_on)

        if success:
            self.info_label.setText(
                f"{message}\n"
                f"Rows: {len(self.data_manager.merged_data)}, "
                f"Columns: {len(self.data_manager.merged_data.columns)}"
            )
            self.files_changed.emit()
        else:
            QMessageBox.warning(self, "Merge Error", message)


class PlotConfigPanel(QWidget):
    """Panel for configuring plot options."""

    config_changed = pyqtSignal(dict)

    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.data_manager = data_manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Plot type
        type_group = QGroupBox("Plot Type")
        type_layout = QVBoxLayout(type_group)
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Line", "Scatter", "Bar", "Histogram", "Area", "Box"])
        self.plot_type_combo.currentTextChanged.connect(self.emit_config)
        type_layout.addWidget(self.plot_type_combo)
        scroll_layout.addWidget(type_group)

        # Column selection
        col_group = QGroupBox("Column Selection")
        col_layout = QVBoxLayout(col_group)

        col_layout.addWidget(QLabel("X Axis:"))
        self.x_combo = QComboBox()
        self.x_combo.addItem("(Index)")
        self.x_combo.currentTextChanged.connect(self.emit_config)
        col_layout.addWidget(self.x_combo)

        col_layout.addWidget(QLabel("Y Axis (select multiple):"))
        self.y_list = QListWidget()
        self.y_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.y_list.setMaximumHeight(150)
        self.y_list.itemSelectionChanged.connect(self.emit_config)
        col_layout.addWidget(self.y_list)

        scroll_layout.addWidget(col_group)

        # Labels
        label_group = QGroupBox("Labels")
        label_layout = QVBoxLayout(label_group)

        label_layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Plot Title")
        self.title_edit.textChanged.connect(self.emit_config)
        label_layout.addWidget(self.title_edit)

        label_layout.addWidget(QLabel("X Label:"))
        self.xlabel_edit = QLineEdit()
        self.xlabel_edit.setPlaceholderText("X Axis Label")
        self.xlabel_edit.textChanged.connect(self.emit_config)
        label_layout.addWidget(self.xlabel_edit)

        label_layout.addWidget(QLabel("Y Label:"))
        self.ylabel_edit = QLineEdit()
        self.ylabel_edit.setPlaceholderText("Y Axis Label")
        self.ylabel_edit.textChanged.connect(self.emit_config)
        label_layout.addWidget(self.ylabel_edit)

        scroll_layout.addWidget(label_group)

        # Style options
        style_group = QGroupBox("Style Options")
        style_layout = QVBoxLayout(style_group)

        # Line style
        line_layout = QHBoxLayout()
        line_layout.addWidget(QLabel("Line Style:"))
        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(["-", "--", "-.", ":", ""])
        self.line_style_combo.currentTextChanged.connect(self.emit_config)
        line_layout.addWidget(self.line_style_combo)
        style_layout.addLayout(line_layout)

        # Marker
        marker_layout = QHBoxLayout()
        marker_layout.addWidget(QLabel("Marker:"))
        self.marker_combo = QComboBox()
        self.marker_combo.addItems(["", "o", "s", "^", "v", "D", "*", "+", "x"])
        self.marker_combo.currentTextChanged.connect(self.emit_config)
        marker_layout.addWidget(self.marker_combo)
        style_layout.addLayout(marker_layout)

        # Alpha
        alpha_layout = QHBoxLayout()
        alpha_layout.addWidget(QLabel("Opacity:"))
        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(0.1, 1.0)
        self.alpha_spin.setSingleStep(0.1)
        self.alpha_spin.setValue(1.0)
        self.alpha_spin.valueChanged.connect(self.emit_config)
        alpha_layout.addWidget(self.alpha_spin)
        style_layout.addLayout(alpha_layout)

        # Grid
        self.grid_check = QCheckBox("Show Grid")
        self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(self.emit_config)
        style_layout.addWidget(self.grid_check)

        # Legend
        self.legend_check = QCheckBox("Show Legend")
        self.legend_check.setChecked(True)
        self.legend_check.stateChanged.connect(self.emit_config)
        style_layout.addWidget(self.legend_check)

        scroll_layout.addWidget(style_group)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def update_columns(self):
        """Update column selections based on merged data."""
        # Store current selections
        current_x = self.x_combo.currentText()
        current_y = [item.text() for item in self.y_list.selectedItems()]

        # Update X combo
        self.x_combo.clear()
        self.x_combo.addItem("(Index)")
        columns = self.data_manager.get_merged_columns()
        self.x_combo.addItems(columns)

        # Restore X selection if possible
        idx = self.x_combo.findText(current_x)
        if idx >= 0:
            self.x_combo.setCurrentIndex(idx)

        # Update Y list
        self.y_list.clear()
        numeric_columns = self.data_manager.get_numeric_columns()
        for col in numeric_columns:
            item = QListWidgetItem(col)
            self.y_list.addItem(item)
            if col in current_y:
                item.setSelected(True)

    def get_config(self) -> dict:
        """Get current plot configuration."""
        x_col = self.x_combo.currentText()
        if x_col == "(Index)":
            x_col = None

        y_cols = [item.text() for item in self.y_list.selectedItems()]

        return {
            "plot_type": self.plot_type_combo.currentText(),
            "x_column": x_col,
            "y_columns": y_cols,
            "title": self.title_edit.text(),
            "xlabel": self.xlabel_edit.text(),
            "ylabel": self.ylabel_edit.text(),
            "grid": self.grid_check.isChecked(),
            "legend": self.legend_check.isChecked(),
            "marker": self.marker_combo.currentText(),
            "line_style": self.line_style_combo.currentText(),
            "alpha": self.alpha_spin.value()
        }

    def emit_config(self):
        """Emit the current configuration."""
        self.config_changed.emit(self.get_config())


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        self.setup_ui()
        self.setup_menu()
        self.connect_signals()

    def setup_ui(self):
        self.setWindowTitle("CSV Plotter")
        self.setMinimumSize(1200, 800)

        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - tabs for file and plot config
        left_panel = QTabWidget()
        left_panel.setMaximumWidth(400)

        self.file_panel = FilePanel(self.data_manager)
        left_panel.addTab(self.file_panel, "Data")

        self.config_panel = PlotConfigPanel(self.data_manager)
        left_panel.addTab(self.config_panel, "Plot Settings")

        splitter.addWidget(left_panel)

        # Right panel - plot canvas
        plot_panel = QWidget()
        plot_layout = QVBoxLayout(plot_panel)

        self.canvas = PlotCanvas()
        self.toolbar = NavigationToolbar(self.canvas, self)

        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        # Save buttons
        save_layout = QHBoxLayout()
        self.save_png_btn = QPushButton("Save as PNG")
        self.save_png_btn.clicked.connect(lambda: self.save_plot("png"))
        self.save_svg_btn = QPushButton("Save as SVG")
        self.save_svg_btn.clicked.connect(lambda: self.save_plot("svg"))
        save_layout.addStretch()
        save_layout.addWidget(self.save_png_btn)
        save_layout.addWidget(self.save_svg_btn)
        plot_layout.addLayout(save_layout)

        splitter.addWidget(plot_panel)
        splitter.setSizes([350, 850])

        main_layout.addWidget(splitter)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready - Load CSV files to begin")

    def setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open CSV...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.file_panel.add_files)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_png_action = QAction("Save Plot as PNG...", self)
        save_png_action.setShortcut("Ctrl+S")
        save_png_action.triggered.connect(lambda: self.save_plot("png"))
        file_menu.addAction(save_png_action)

        save_svg_action = QAction("Save Plot as SVG...", self)
        save_svg_action.setShortcut("Ctrl+Shift+S")
        save_svg_action.triggered.connect(lambda: self.save_plot("svg"))
        file_menu.addAction(save_svg_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def connect_signals(self):
        """Connect signals between components."""
        self.file_panel.files_changed.connect(self.on_data_changed)
        self.config_panel.config_changed.connect(self.update_plot)

    def on_data_changed(self):
        """Handle data changes."""
        self.config_panel.update_columns()
        self.update_plot(self.config_panel.get_config())

        if self.data_manager.merged_data is not None:
            rows = len(self.data_manager.merged_data)
            cols = len(self.data_manager.merged_data.columns)
            self.statusBar.showMessage(f"Data loaded: {rows} rows, {cols} columns")
        else:
            self.statusBar.showMessage("Ready - Load CSV files to begin")

    def update_plot(self, config: dict):
        """Update the plot with current configuration."""
        self.canvas.update_plot(self.data_manager.merged_data, config)

    def save_plot(self, format_type: str):
        """Save the current plot to a file."""
        if format_type == "png":
            filter_str = "PNG Image (*.png)"
            default_ext = ".png"
        else:
            filter_str = "SVG Image (*.svg)"
            default_ext = ".svg"

        filepath, _ = QFileDialog.getSaveFileName(
            self, f"Save Plot as {format_type.upper()}",
            f"plot{default_ext}", filter_str
        )

        if filepath:
            try:
                self.canvas.save_plot(filepath)
                self.statusBar.showMessage(f"Plot saved to {filepath}")
                QMessageBox.information(self, "Success", f"Plot saved to:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plot: {str(e)}")

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About CSV Plotter",
            "CSV Plotter v1.0\n\n"
            "A Python GUI application for loading, merging, and plotting CSV data.\n\n"
            "Features:\n"
            "• Load multiple CSV files\n"
            "• Merge files with various options\n"
            "• Multiple plot types\n"
            "• Real-time plot updates\n"
            "• Export to PNG or SVG"
        )


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
