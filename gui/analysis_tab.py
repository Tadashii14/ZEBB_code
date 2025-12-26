"""
Analysis Tab for ZIMON

Provides behavioral analysis capabilities using ZebraZoom integration.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QGroupBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QProgressBar, QComboBox, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import logging
import os
from pathlib import Path

logger = logging.getLogger("analysis_tab")


class AnalysisWorker(QThread):
    """Worker thread for running analysis"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, zebrazoom_integration, video_path, config_path=None):
        super().__init__()
        self.zebrazoom = zebrazoom_integration
        self.video_path = video_path
        self.config_path = config_path
    
    def run(self):
        try:
            self.status.emit("Starting analysis...")
            self.progress.emit(10)
            
            # Run analysis
            result = self.zebrazoom.analyze_video(
                self.video_path,
                self.config_path
            )
            
            self.progress.emit(100)
            self.status.emit("Analysis complete")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class AnalysisTab(QWidget):
    """Analysis tab widget"""
    
    def __init__(self, zebrazoom_integration=None):
        super().__init__()
        self.zebrazoom = zebrazoom_integration
        self.current_data = None
        self.bouts = []
        self.video_path = None
        self.config_path = None
        
        self._build_ui()
        
        # Show warning if ZebraZoom not available
        if not self.zebrazoom or not self.zebrazoom.is_available():
            self._show_zebrazoom_warning()
    
    def _show_zebrazoom_warning(self):
        """Show warning that ZebraZoom is not available"""
        warning_label = QLabel(
            "⚠️ ZebraZoom is not available.\n"
            "Please install ZebraZoom or specify its path in Settings (⚙ icon)."
        )
        warning_label.setStyleSheet("""
            color: #f5c542;
            font-size: 12px;
            padding: 12px;
            background: #2b2f3a;
            border-radius: 8px;
            border: 1px solid #f5c542;
        """)
        warning_label.setWordWrap(True)
        
        # Insert at the top
        layout = self.layout()
        layout.insertWidget(0, warning_label)
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)
        
        # Header
        header = QLabel("Behavioral Analysis")
        header.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff; padding: 8px 0px;")
        layout.addWidget(header)
        
        # File selection section
        file_section = QGroupBox("Video Analysis")
        file_layout = QVBoxLayout(file_section)
        file_layout.setContentsMargins(16, 20, 16, 16)
        file_layout.setSpacing(12)
        
        # Video file selection
        video_layout = QHBoxLayout()
        video_layout.setSpacing(10)
        
        self.video_path_label = QLabel("No video selected")
        self.video_path_label.setStyleSheet("color: #9aa0aa; padding: 4px;")
        video_btn = QPushButton("Select Video")
        video_btn.clicked.connect(self._select_video)
        video_btn.setMinimumWidth(120)
        
        video_layout.addWidget(QLabel("Video:"))
        video_layout.addWidget(self.video_path_label, 1)
        video_layout.addWidget(video_btn)
        
        file_layout.addLayout(video_layout)
        
        # Config file selection
        config_layout = QHBoxLayout()
        config_layout.setSpacing(10)
        
        self.config_path_label = QLabel("Using default config")
        self.config_path_label.setStyleSheet("color: #9aa0aa; padding: 4px;")
        config_btn = QPushButton("Select Config")
        config_btn.clicked.connect(self._select_config)
        config_btn.setMinimumWidth(120)
        
        config_layout.addWidget(QLabel("Config:"))
        config_layout.addWidget(self.config_path_label, 1)
        config_layout.addWidget(config_btn)
        
        file_layout.addLayout(config_layout)
        
        # Analyze button
        self.analyze_btn = QPushButton("▶ Run Analysis")
        self.analyze_btn.setMinimumHeight(40)
        self.analyze_btn.clicked.connect(self._run_analysis)
        file_layout.addWidget(self.analyze_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        file_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #9aa0aa; font-size: 11px;")
        file_layout.addWidget(self.status_label)
        
        layout.addWidget(file_section)
        
        # Results section
        results_section = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout(results_section)
        results_layout.setContentsMargins(16, 20, 16, 16)
        results_layout.setSpacing(12)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Parameter", "Value", "Unit", "Notes"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_section)
        
        # Bout detection section
        bout_section = QGroupBox("Bout Detection")
        bout_layout = QVBoxLayout(bout_section)
        bout_layout.setContentsMargins(16, 20, 16, 16)
        bout_layout.setSpacing(12)
        
        # Parameters
        params_layout = QHBoxLayout()
        params_layout.setSpacing(10)
        
        params_layout.addWidget(QLabel("Min Distance:"))
        self.min_distance_spin = QSpinBox()
        self.min_distance_spin.setRange(1, 100)
        self.min_distance_spin.setValue(5)
        self.min_distance_spin.setSuffix(" px")
        params_layout.addWidget(self.min_distance_spin)
        
        params_layout.addWidget(QLabel("Min Frames:"))
        self.min_frames_spin = QSpinBox()
        self.min_frames_spin.setRange(1, 100)
        self.min_frames_spin.setValue(10)
        params_layout.addWidget(self.min_frames_spin)
        
        params_layout.addStretch()
        
        detect_btn = QPushButton("Detect Bouts")
        detect_btn.clicked.connect(self._detect_bouts)
        params_layout.addWidget(detect_btn)
        
        bout_layout.addLayout(params_layout)
        
        # Bout results
        self.bout_count_label = QLabel("Bouts detected: 0")
        self.bout_count_label.setStyleSheet("color: #4fc3f7; font-weight: 600;")
        bout_layout.addWidget(self.bout_count_label)
        
        layout.addWidget(bout_section)
        
        # Clustering section
        cluster_section = QGroupBox("Behavioral Clustering")
        cluster_layout = QVBoxLayout(cluster_section)
        cluster_layout.setContentsMargins(16, 20, 16, 16)
        cluster_layout.setSpacing(12)
        
        cluster_params = QHBoxLayout()
        cluster_params.setSpacing(10)
        
        cluster_params.addWidget(QLabel("Number of Clusters:"))
        self.n_clusters_spin = QSpinBox()
        self.n_clusters_spin.setRange(2, 20)
        self.n_clusters_spin.setValue(5)
        cluster_params.addWidget(self.n_clusters_spin)
        
        cluster_params.addStretch()
        
        cluster_btn = QPushButton("Cluster Bouts")
        cluster_btn.clicked.connect(self._cluster_bouts)
        cluster_params.addWidget(cluster_btn)
        
        cluster_layout.addLayout(cluster_params)
        
        self.cluster_results_label = QLabel("")
        self.cluster_results_label.setStyleSheet("color: #9aa0aa;")
        cluster_layout.addWidget(self.cluster_results_label)
        
        layout.addWidget(cluster_section)
        
        layout.addStretch()
    
    def _select_video(self):
        """Select video file for analysis"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.avi *.mp4 *.mov *.mkv);;All Files (*)"
        )
        
        if file_path:
            self.video_path_label.setText(os.path.basename(file_path))
            self.video_path_label.setToolTip(file_path)
            self.video_path = file_path
    
    def _select_config(self):
        """Select ZebraZoom config file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Config File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.config_path_label.setText(os.path.basename(file_path))
            self.config_path_label.setToolTip(file_path)
            self.config_path = file_path
        else:
            self.config_path = None
            self.config_path_label.setText("Using default config")
    
    def _run_analysis(self):
        """Run ZebraZoom analysis on selected video"""
        if not hasattr(self, 'video_path') or not self.video_path:
            QMessageBox.warning(self, "No Video", "Please select a video file first")
            return
        
        if not self.zebrazoom or not self.zebrazoom.is_available():
            QMessageBox.warning(
                self,
                "ZebraZoom Not Available",
                "ZebraZoom is not installed or not found.\n\n"
                "Please install ZebraZoom or specify its path in settings."
            )
            return
        
        # Disable button and show progress
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Preparing analysis...")
        
        # Create worker thread
        self.worker = AnalysisWorker(
            self.zebrazoom,
            self.video_path,
            getattr(self, 'config_path', None)
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_analysis_finished)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.start()
    
    def _on_analysis_finished(self, result):
        """Handle analysis completion"""
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Analysis completed successfully")
        
        # Display results
        self._display_results(result)
        
        QMessageBox.information(self, "Analysis Complete", "Video analysis completed successfully!")
    
    def _on_analysis_error(self, error_msg):
        """Handle analysis error"""
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error_msg}")
        
        QMessageBox.critical(self, "Analysis Error", f"Analysis failed:\n{error_msg}")
    
    def _display_results(self, result):
        """Display analysis results in table"""
        # Clear existing results
        self.results_table.setRowCount(0)
        
        # Add result rows (simplified - would parse actual ZebraZoom output)
        if isinstance(result, dict):
            row = 0
            for key, value in result.items():
                if key not in ['status', 'video', 'output']:
                    self.results_table.insertRow(row)
                    self.results_table.setItem(row, 0, QTableWidgetItem(str(key)))
                    self.results_table.setItem(row, 1, QTableWidgetItem(str(value)))
                    self.results_table.setItem(row, 2, QTableWidgetItem(""))
                    self.results_table.setItem(row, 3, QTableWidgetItem(""))
                    row += 1
    
    def _detect_bouts(self):
        """Detect movement bouts from tracking data"""
        if self.current_data is None:
            QMessageBox.warning(self, "No Data", "Please run analysis first")
            return
        
        try:
            min_distance = self.min_distance_spin.value()
            min_frames = self.min_frames_spin.value()
            
            self.bouts = self.zebrazoom.detect_bouts(
                self.current_data,
                min_distance=min_distance,
                min_frames=min_frames
            )
            
            self.bout_count_label.setText(f"Bouts detected: {len(self.bouts)}")
            self.status_label.setText(f"Detected {len(self.bouts)} movement bouts")
            
        except Exception as e:
            logger.error(f"Error detecting bouts: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Bout detection failed:\n{str(e)}")
    
    def _cluster_bouts(self):
        """Cluster detected bouts"""
        if not self.bouts:
            QMessageBox.warning(self, "No Bouts", "Please detect bouts first")
            return
        
        try:
            n_clusters = self.n_clusters_spin.value()
            
            cluster_result = self.zebrazoom.cluster_bouts(
                self.bouts,
                n_clusters=n_clusters
            )
            
            # Display cluster results
            cluster_info = f"Clustered {len(self.bouts)} bouts into {n_clusters} clusters"
            self.cluster_results_label.setText(cluster_info)
            self.status_label.setText(cluster_info)
            
        except Exception as e:
            logger.error(f"Error clustering bouts: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Clustering failed:\n{str(e)}")

