import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QDoubleSpinBox, QSpinBox, QPushButton, QFileDialog,
                             QMessageBox, QDialog)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QPalette, QColor, QFont, QPixmap, QTransform
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from scipy import stats # NEW IMPORT for Normality Test

# --- 全局设置 ---
plt.rcParams['font.sans-serif'] = ['Arial', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = '#1a1a2e'
plt.rcParams['axes.facecolor'] = '#16213e'
plt.rcParams['text.color'] = '#e0e0e0'
plt.rcParams['axes.labelcolor'] = '#f0f0f0'
plt.rcParams['xtick.color'] = '#d0d0d0'
plt.rcParams['ytick.color'] = '#d0d0d0'
plt.rcParams['legend.labelcolor'] = '#f0f0f0'


# --- NEW: Love, Death & Robots Style Opening Dialog ---
class StatsOpeningScreen(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading...")
        self.setFixedSize(600, 300)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background-color: #000000;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(50)

        # Statistical symbols for the three wheels
        self.symbols = ['μ', 'σ', 'N', 'Σ', '∞', '∫', 'χ²']
        self.widgets = []
        self.animations = []
        
        # Create and set up the three rotating wheels
        for i in range(3):
            label = QLabel(self.symbols[i])
            label.setFont(QFont("Arial", 80, QFont.Weight.Bold))
            label.setStyleSheet("color: #FF073A;") # Neon Red/Pink
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.widgets.append(label)
            main_layout.addWidget(label)
            
            # Rotation Animation setup
            anim = QPropertyAnimation(label, b"rotation")
            anim.setDuration(3000) # 3 seconds per rotation cycle
            anim.setLoopCount(-1)  # Loop indefinitely
            anim.setStartValue(0)
            anim.setEndValue(360 if i % 2 == 0 else -360) # Alternate rotation direction
            anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            self.animations.append(anim)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_symbol)
        self.animation_timer.start(500) # Change symbol every 0.5 seconds
        
        # Start all animations
        for anim in self.animations:
            anim.start()

        # Timer to close the dialog after a few seconds
        QTimer.singleShot(4000, self.close) 

    # Custom property setter for rotation (Qt doesn't have a built-in rotation property for QLabel)
    def setRotation(self, angle):
        # We need to apply the rotation via a QTransform
        sender_label = self.sender()
        transform = QTransform()
        transform.rotate(angle)
        sender_label.setPixmap(QPixmap(sender_label.pixmap().size()).transformed(transform))

        # Update symbol if the rotation property is being animated
        if angle % 100 == 0:
             self.update_symbol()


    # Update the symbol inside the spinning wheel
    def update_symbol(self):
        import random
        for widget in self.widgets:
            widget.setText(random.choice(self.symbols))


# --- Main Application Window ---
class DarkNormalDistributionGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Show the opening screen first
        self.opening_screen = StatsOpeningScreen()
        self.opening_screen.exec() 
        
        self.setWindowTitle("Advanced Normal Distribution Generator")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(QSize(1000, 600))
        self.setStyleSheet("background-color: #121212;")
        
        # --- Data Storage and State ---
        self.data = None
        self.calculated_mean = 0.0
        self.calculated_std = 0.0
        self.calculated_size = 0
        # -----------------------------------
        
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- 左侧参数编辑区 ---
        control_layout = QVBoxLayout()
        control_layout.setSpacing(22)
        control_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_label = QLabel("<h3 style='color:#4cc9f0; margin:0; text-align:center; font-weight:bold'>Parameters & Data Load</h3>")
        control_layout.addWidget(title_label)
        
        load_data_btn = QPushButton("Load Data File (.csv, .txt)")
        load_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef476f;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px 30px;
                font-size: 15px;
                font-weight: 700;
                margin-bottom: 25px;
                border: 1px solid rgba(239, 71, 111, 0.5);
            }
            QPushButton:hover {
                background-color: #d62828;
                border-color: rgba(214, 40, 40, 0.8);
            }
            QPushButton:pressed {
                background-color: #b7094c;
                border-color: #b7094c;
            }
        """)
        load_data_btn.clicked.connect(self.load_data)
        control_layout.addWidget(load_data_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Display Calculated Statistics ---
        self.mean_label = self.create_stats_label("Mean (μ): N/A")
        self.std_label = self.create_stats_label("Std Dev (σ): N/A")
        self.size_label = self.create_stats_label("Sample Size: N/A")
        # --- NEW: Normality Test Result Label ---
        self.normality_label = self.create_stats_label("Normality: Needs Data", border_color="#ffd166")
        
        control_layout.addWidget(self.mean_label)
        control_layout.addWidget(self.std_label)
        control_layout.addWidget(self.size_label)
        control_layout.addWidget(self.normality_label) # Add the new label
        # -------------------------------------

        generate_btn = QPushButton("Generate Curve")
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4361ee;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px 30px;
                font-size: 15px;
                font-weight: 700;
                margin-top: 15px;
                border: 1px solid rgba(67, 97, 238, 0.5);
            }
            QPushButton:hover {
                background-color: #3a0ca3;
                border-color: rgba(58, 12, 163, 0.8);
            }
            QPushButton:pressed {
                background-color: #2b2d42;
                border-color: #2b2d42;
            }
        """)
        generate_btn.clicked.connect(self.update_plot)
        control_layout.addWidget(generate_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        left_widget = QWidget()
        left_widget.setLayout(control_layout)
        left_widget.setMaximumWidth(280)
        left_widget.setStyleSheet("""
            background-color: #1e1e2e; 
            border-radius: 12px; 
            padding: 20px; 
            border: 1px solid #2d2d44;
        """)
        main_layout.addWidget(left_widget)

        # --- 右侧图像显示区 ---
        self.figure, self.ax = plt.subplots(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        self.toolbar.setStyleSheet("""
            QToolBar { background-color: #1e1e2e; border: 1px solid #2d2d44; }
            QToolButton { color: #e0e0e0; background-color: transparent; }
            QToolButton:hover { color: #4cc9f0; background-color: #2d2d44; border-radius: 6px; }
        """)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.toolbar)
        
        canvas_container = QWidget()
        canvas_container.setStyleSheet("""
            background-color: #16213e; 
            border-radius: 12px; 
            padding: 15px; 
            border: 1px solid #2d2d44;
        """)
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.addWidget(self.canvas)
        right_layout.addWidget(canvas_container, stretch=1)
        
        main_layout.addLayout(right_layout, stretch=1)

        # Initial blank plot
        self.ax.set_title("Load data to begin", fontsize=18, fontweight='bold', color='#f0f0f0')
        self.canvas.draw()
        
    def create_stats_label(self, text, border_color="#4cc9f0"):
        label = QLabel(f"<span style='color:#f0f0f0; font-size:16px; font-weight:700'>{text}</span>")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label.setWordWrap(True)
        label.setContentsMargins(10, 5, 10, 5)
        label.setStyleSheet(f"""
            QLabel {{
                background-color: #2d2d44;
                border-radius: 6px;
                padding: 10px;
                border-left: 5px solid {border_color};
            }}
        """)
        return label

    def load_data(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Data File", "", 
                                                  "Data Files (*.csv *.txt);;All Files (*)")
        if filepath:
            try:
                # Assuming the data file is a single column of numbers
                loaded_data = np.loadtxt(filepath, delimiter=',', usecols=0)
                
                if len(loaded_data) < 3: # Shapiro-Wilk requires at least 3 data points
                    QMessageBox.warning(self, "Load Error", "The file must contain at least three data points for analysis.")
                    return

                self.data = loaded_data
                self.calculate_and_update_stats()
                QMessageBox.information(self, "Success", f"Data loaded successfully. Sample Size: {self.calculated_size}")
                self.update_plot()
                
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Could not load or parse the data file.\nError: {e}")

    def calculate_and_update_stats(self):
        """Calculates mean, std dev, size, and runs normality test."""
        if self.data is not None:
            self.calculated_mean = np.mean(self.data)
            self.calculated_std = np.std(self.data)
            self.calculated_size = len(self.data)
        
        # Update standard display labels
        self.mean_label.setText(f"<span style='color:#f0f0f0; font-size:16px; font-weight:700'>Mean (μ): {self.calculated_mean:.4f}</span>")
        self.std_label.setText(f"<span style='color:#f0f0f0; font-size:16px; font-weight:700'>Std Dev (σ): {self.calculated_std:.4f}</span>")
        self.size_label.setText(f"<span style='color:#f0f0f0; font-size:16px; font-weight:700'>Sample Size: {self.calculated_size}</span>")
        
        # --- NEW: Normality Test and Update ---
        self.run_normality_test()

    def run_normality_test(self):
        """Performs the Shapiro-Wilk test and updates the normality label."""
        if self.data is None or self.calculated_size < 3:
            self.normality_label.setText("Normality: Insufficient Data")
            self.normality_label.setStyleSheet(f"""QLabel {{background-color: #2d2d44; border-radius: 6px; padding: 10px; border-left: 5px solid #ffd166;}}""")
            return

        # Shapiro-Wilk Test: Returns (W-statistic, p-value)
        # Note: Shapiro-Wilk is most reliable for sample sizes up to N=5000. 
        # For larger datasets (N > 5000), it's still a good indicator, 
        # but often indicates non-normality because large sample sizes make 
        # even small deviations from normal statistically significant.
        try:
            # Only use the first 5000 points for the Shapiro-Wilk test if the dataset is massive
            test_data = self.data[:5000] if self.calculated_size > 5000 else self.data
            W_statistic, p_value = stats.shapiro(test_data)
        except Exception as e:
             # Handle case where test fails (e.g., all data points are the same)
             self.normality_label.setText("Normality: Test Failed (data likely constant)")
             return

        # Significance Level (Alpha)
        alpha = 0.05
        
        if p_value > alpha:
            # The null hypothesis (data is normally distributed) cannot be rejected.
            result_text = "NORMAL (p > 0.05)"
            deviation_text = "Excellent Fit."
            border_color = "#3a86ff" # Blue (Good)
        else:
            # The null hypothesis is rejected.
            result_text = "NOT NORMAL (p < 0.05)"
            
            # Quantify non-normality based on p-value
            if p_value > 0.01:
                deviation_text = f"Minor Deviation, p={p_value:.3f}"
                border_color = "#ffd166" # Yellow (Warning)
            elif p_value > 1e-4:
                deviation_text = f"Moderate Deviation, p={p_value:.2e}"
                border_color = "#ff6b35" # Orange (Concern)
            else:
                deviation_text = f"Significant Deviation, p={p_value:.2e}"
                border_color = "#ef476f" # Red (Bad)

        # Update the display label
        final_text = (f"<span style='color:#f0f0f0; font-size:16px; font-weight:700'>Normality: {result_text}</span><br>"
                      f"<span style='color:#d0d0d0; font-size:12px;'>{deviation_text}</span>")
                      
        self.normality_label.setText(final_text)
        self.normality_label.setStyleSheet(f"""QLabel {{background-color: #2d2d44; border-radius: 6px; padding: 10px; border-left: 5px solid {border_color};}}""")
        # ---------------------------------------------

    def update_plot(self):
        # ... (rest of update_plot remains the same, using self.data, self.calculated_mean, etc.) ...
        
        mean = self.calculated_mean
        std = self.calculated_std
        data = self.data

        if data is None:
             QMessageBox.warning(self, "Plot Error", "No data available to plot. Please load a data file.")
             return
             
        self.ax.clear()

        # Generate Histogram from actual data
        n, bins, patches = self.ax.hist(data, bins='auto', density=True, alpha=0.5, color='#4cc9f0', edgecolor='#3a86ff', label='Data Histogram')
        
        # Calculate the theoretical normal distribution curve
        x = np.linspace(bins.min(), bins.max(), 1000)
        y = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)
        self.ax.plot(x, y, color='#f72585', linewidth=4, label=f'Normal Curve (μ={mean:.2f}, σ={std:.2f})', alpha=0.9)

        self.ax.set_title("Normal Distribution Visualization (Calculated from Data)", fontsize=18, fontweight='bold', color='#f0f0f0')
        self.ax.set_xlabel("Value", fontsize=15, color='#f0f0f0')
        self.ax.set_ylabel("Probability Density", fontsize=15, color='#f0f0f0')
        self.ax.legend(fontsize=13, loc='upper right', frameon=True, facecolor='#2d2d44', edgecolor='#4361ee')
        self.ax.grid(True, alpha=0.2, linestyle='--', color='#444444')
        self.ax.tick_params(axis='both', which='major', labelsize=12, width=2, length=6)

        self.figure.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    import random # Import needed for the opening screen to work

    # Register the custom rotation property (necessary for QPropertyAnimation)
    # The animation code needs a property to hook onto, even if we manually handle the rotation in setRotation
    try:
        if not hasattr(QLabel, 'rotation'):
            from PyQt6.QtCore import pyqtProperty
            QLabel.rotation = pyqtProperty(float, fset=StatsOpeningScreen.setRotation)
    except Exception:
        pass # Ignore if it fails, the core functionality will still work without smooth animation
    
    app = QApplication(sys.argv)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 18))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
    app.setPalette(palette)
    window = DarkNormalDistributionGenerator()
    window.show()
    sys.exit(app.exec())