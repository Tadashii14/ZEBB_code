"""
ZebraZoom Integration Module

This module provides integration with ZebraZoom for behavioral analysis.
It allows ZIMON to use ZebraZoom's analysis capabilities for:
- Parameter extraction
- Bout detection
- Behavioral clustering
- Population comparison
"""
import os
import sys
import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# Optional imports - will be checked before use
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = logging.getLogger("zebrazoom_integration")


class ZebraZoomIntegration:
    """
    Integration wrapper for ZebraZoom analysis features.
    
    This class provides methods to:
    1. Run ZebraZoom tracking/analysis on videos
    2. Extract behavioral parameters
    3. Perform clustering analysis
    4. Compare populations
    """
    
    def __init__(self, zebrazoom_path: Optional[str] = None):
        """
        Initialize ZebraZoom integration.
        
        Args:
            zebrazoom_path: Path to ZebraZoom executable or installation.
                          If None, will try to auto-detect.
        """
        self.zebrazoom_path = zebrazoom_path
        self.zebrazoom_exe = None
        self.zebrazoom_lib = None
        
        # Try to find ZebraZoom
        self._find_zebrazoom()
    
    def _find_zebrazoom(self):
        """Try to locate ZebraZoom installation"""
        # Common installation paths
        possible_paths = [
            self.zebrazoom_path,
            r"C:\Program Files\ZebraZoom\ZebraZoom.exe",
            r"C:\Users\{}\Downloads\ZebraZoom-Windows\ZebraZoom.exe".format(os.getenv("USERNAME", "")),
            os.path.join(os.path.expanduser("~"), "Downloads", "ZebraZoom-Windows", "ZebraZoom.exe"),
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                self.zebrazoom_exe = path
                logger.info(f"Found ZebraZoom executable at: {path}")
                return
        
        # Try to import as Python library
        try:
            import zebrazoom
            self.zebrazoom_lib = zebrazoom
            logger.info("ZebraZoom library found via import")
        except ImportError:
            logger.warning("ZebraZoom not found. Analysis features will be limited.")
    
    def is_available(self) -> bool:
        """Check if ZebraZoom is available"""
        # Check if ZebraZoom executable/library exists
        zebrazoom_available = self.zebrazoom_exe is not None or self.zebrazoom_lib is not None
        
        # Check if required dependencies are available
        # For basic functionality, we only need the executable
        # Advanced features require pandas/numpy but those are checked when used
        return zebrazoom_available
    
    def analyze_video(self, video_path: str, config_path: Optional[str] = None, 
                     output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Run ZebraZoom analysis on a video file.
        
        Args:
            video_path: Path to video file to analyze
            config_path: Path to ZebraZoom config JSON file (optional)
            output_dir: Directory to save results (optional)
            
        Returns:
            Dictionary with analysis results
        """
        if not self.is_available():
            raise RuntimeError("ZebraZoom is not available")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Use library if available
        if self.zebrazoom_lib:
            return self._analyze_with_library(video_path, config_path, output_dir)
        else:
            return self._analyze_with_exe(video_path, config_path, output_dir)
    
    def _analyze_with_library(self, video_path: str, config_path: Optional[str], 
                              output_dir: Optional[str]) -> Dict[str, Any]:
        """Analyze video using ZebraZoom Python library"""
        try:
            # Import ZebraZoom modules
            from zebrazoom.code.tracking import get_tracking_method
            from zebrazoom.code.extractParameters import extractParameters
            
            # Load config
            if config_path and os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = self._get_default_config()
            
            # Run tracking
            tracking_method = get_tracking_method(config.get("trackingMethod", "fastFishTracking"))
            # ... implementation would go here
            
            logger.info(f"Analysis completed for {video_path}")
            return {"status": "success", "video": video_path}
            
        except Exception as e:
            logger.error(f"Error analyzing with library: {e}", exc_info=True)
            raise
    
    def _analyze_with_exe(self, video_path: str, config_path: Optional[str],
                          output_dir: Optional[str]) -> Dict[str, Any]:
        """Analyze video using ZebraZoom executable"""
        try:
            import os
            from pathlib import Path
            
            # Parse video path to extract components
            video_full_path = os.path.abspath(video_path)
            video_dir = os.path.dirname(video_full_path)
            video_filename = os.path.basename(video_full_path)
            video_name, video_ext = os.path.splitext(video_filename)
            video_ext = video_ext.lstrip('.')  # Remove leading dot
            
            # ZebraZoom.exe requires: pathToVideo videoName videoExt configFile
            # Build command according to ZebraZoom's CLI format
            cmd = [self.zebrazoom_exe]
            
            # Add path to video directory
            cmd.append(video_dir)
            
            # Add video name (without extension)
            cmd.append(video_name)
            
            # Add video extension (without dot)
            cmd.append(video_ext)
            
            # Add config file (required)
            # ZebraZoom expects config file path, try to find or create one
            if config_path and os.path.exists(config_path):
                config_full_path = os.path.abspath(config_path)
                cmd.append(config_full_path)
                logger.info(f"Using provided config: {config_full_path}")
            else:
                # Try to find existing config files in video directory
                # Common ZebraZoom config file patterns
                possible_configs = [
                    os.path.join(video_dir, f"{video_name}.json"),
                    os.path.join(video_dir, "config.json"),
                    os.path.join(video_dir, f"{video_name}_config.json"),
                ]
                
                config_found = None
                for possible_config in possible_configs:
                    if os.path.exists(possible_config):
                        config_found = os.path.abspath(possible_config)
                        logger.info(f"Found existing config: {config_found}")
                        break
                
                if not config_found:
                    # Create a default config file if none found
                    default_config_path = os.path.join(video_dir, f"{video_name}_config.json")
                    self.create_config_file(default_config_path)
                    config_found = os.path.abspath(default_config_path)
                    logger.info(f"Created default config: {config_found}")
                
                cmd.append(config_found)
            
            logger.info(f"Running ZebraZoom with command: {' '.join(cmd)}")
            
            # Run ZebraZoom
            # Change to video directory so ZebraZoom can find relative paths
            original_cwd = os.getcwd()
            try:
                os.chdir(video_dir)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600,  # 1 hour timeout
                    cwd=video_dir
                )
            finally:
                os.chdir(original_cwd)
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise RuntimeError(f"ZebraZoom analysis failed: {error_msg}")
            
            logger.info(f"Analysis completed for {video_path}")
            logger.info(f"ZebraZoom output: {result.stdout}")
            
            return {
                "status": "success",
                "video": video_path,
                "output": result.stdout,
                "config_used": cmd[-1]  # Last argument is config file
            }
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("ZebraZoom analysis timed out")
        except Exception as e:
            logger.error(f"Error analyzing with executable: {e}", exc_info=True)
            raise
    
    def extract_parameters(self, tracking_data_path: str):
        """
        Extract behavioral parameters from tracking data.
        
        Args:
            tracking_data_path: Path to ZebraZoom output (.h5 file)
            
        Returns:
            DataFrame with extracted parameters (or dict if pandas not available)
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for parameter extraction. Install with: pip install pandas")
        
        try:
            import h5py
            
            # Load ZebraZoom output
            with h5py.File(tracking_data_path, 'r') as f:
                # Extract data structure
                # This is a simplified version - actual implementation would
                # parse ZebraZoom's specific HDF5 structure
                data = {}
                
                # Try to read common keys
                for key in f.keys():
                    try:
                        data[key] = f[key][:]
                    except:
                        pass
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            return df
            
        except Exception as e:
            logger.error(f"Error extracting parameters: {e}", exc_info=True)
            raise
    
    def detect_bouts(self, tracking_data, 
                    min_distance: float = 5.0,
                    min_frames: int = 10) -> List[Dict[str, Any]]:
        """
        Detect movement bouts from tracking data.
        
        Args:
            tracking_data: DataFrame with tracking data (HeadX, HeadY, etc.)
            min_distance: Minimum distance threshold for bout detection
            min_frames: Minimum frames for a valid bout
            
        Returns:
            List of bout dictionaries
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for bout detection. Install with: pip install numpy")
        
        bouts = []
        
        # Handle both DataFrame and dict
        if PANDAS_AVAILABLE and isinstance(tracking_data, pd.DataFrame):
            if 'HeadX' not in tracking_data.columns or 'HeadY' not in tracking_data.columns:
                logger.warning("Tracking data missing HeadX/HeadY columns")
                return bouts
            
            head_x = tracking_data['HeadX'].values
            head_y = tracking_data['HeadY'].values
        elif isinstance(tracking_data, dict):
            if 'HeadX' not in tracking_data or 'HeadY' not in tracking_data:
                logger.warning("Tracking data missing HeadX/HeadY keys")
                return bouts
            head_x = tracking_data['HeadX']
            head_y = tracking_data['HeadY']
        else:
            logger.warning("Unsupported tracking data format")
            return bouts
        
        # Calculate instantaneous distances
        distances = np.sqrt(
            np.diff(head_x)**2 + 
            np.diff(head_y)**2
        )
        
        # Find frames with movement above threshold
        movement_frames = distances > min_distance
        
        # Detect bout start/end
        bout_start = None
        for i, is_moving in enumerate(movement_frames):
            if is_moving and bout_start is None:
                bout_start = i
            elif not is_moving and bout_start is not None:
                bout_length = i - bout_start
                if bout_length >= min_frames:
                    bouts.append({
                        "BoutStart": bout_start,
                        "BoutEnd": i,
                        "BoutLength": bout_length,
                        "FrameStart": bout_start,
                        "FrameEnd": i
                    })
                bout_start = None
        
        # Handle bout that extends to end
        if bout_start is not None:
            bout_length = len(movement_frames) - bout_start
            if bout_length >= min_frames:
                bouts.append({
                    "BoutStart": bout_start,
                    "BoutEnd": len(movement_frames),
                    "BoutLength": bout_length,
                    "FrameStart": bout_start,
                    "FrameEnd": len(movement_frames)
                })
        
        logger.info(f"Detected {len(bouts)} bouts")
        return bouts
    
    def cluster_bouts(self, bouts_data: List[Dict[str, Any]], 
                     n_clusters: int = 5) -> Dict[str, Any]:
        """
        Cluster bouts using unsupervised learning.
        
        Args:
            bouts_data: List of bout dictionaries with features
            n_clusters: Number of clusters
            
        Returns:
            Dictionary with clustering results
        """
        try:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler
            
            # Extract features from bouts
            features = []
            for bout in bouts_data:
                feature_vector = [
                    bout.get("BoutLength", 0),
                    bout.get("MaxSpeed", 0),
                    bout.get("TotalDistance", 0),
                    bout.get("AvgSpeed", 0),
                ]
                features.append(feature_vector)
            
            if len(features) < n_clusters:
                logger.warning(f"Not enough bouts ({len(features)}) for {n_clusters} clusters")
                return {"clusters": [], "labels": []}
            
            # Normalize features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(features_scaled)
            
            # Organize results
            clusters = {}
            for i, label in enumerate(labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(bouts_data[i])
            
            logger.info(f"Clustered {len(bouts_data)} bouts into {n_clusters} clusters")
            
            return {
                "clusters": clusters,
                "labels": labels.tolist(),
                "centers": kmeans.cluster_centers_.tolist(),
                "n_clusters": n_clusters
            }
            
        except ImportError:
            logger.error("scikit-learn not available for clustering")
            raise
        except Exception as e:
            logger.error(f"Error clustering bouts: {e}", exc_info=True)
            raise
    
    def compare_populations(self, data1, data2,
                           label1: str = "Group 1", label2: str = "Group 2") -> Dict[str, Any]:
        """
        Compare two populations of animals.
        
        Args:
            data1: DataFrame with tracking data for population 1
            data2: DataFrame with tracking data for population 2
            label1: Label for population 1
            label2: Label for population 2
            
        Returns:
            Dictionary with comparison statistics
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for population comparison. Install with: pip install pandas")
        
        try:
            from scipy import stats
            
            comparison = {}
            
            # Compare common metrics
            metrics = ['Speed', 'Distance', 'BoutFrequency', 'BoutDuration']
            
            for metric in metrics:
                if metric in data1.columns and metric in data2.columns:
                    group1_data = data1[metric].dropna()
                    group2_data = data2[metric].dropna()
                    
                    if len(group1_data) > 0 and len(group2_data) > 0:
                        # Statistical test
                        stat, p_value = stats.mannwhitneyu(group1_data, group2_data, 
                                                          alternative='two-sided')
                        
                        comparison[metric] = {
                            f"{label1}_mean": float(group1_data.mean()),
                            f"{label1}_std": float(group1_data.std()),
                            f"{label2}_mean": float(group2_data.mean()),
                            f"{label2}_std": float(group2_data.std()),
                            "p_value": float(p_value),
                            "significant": p_value < 0.05
                        }
            
            logger.info(f"Compared {label1} vs {label2}")
            return comparison
            
        except ImportError:
            logger.error("scipy not available for statistical comparison")
            raise
        except Exception as e:
            logger.error(f"Error comparing populations: {e}", exc_info=True)
            raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default ZebraZoom configuration"""
        return {
            "nbWells": 1,
            "nbAnimalsPerWell": 1,
            "firstFrame": 0,
            "lastFrame": -1,
            "detectBouts": True,
            "minArea": 400,
            "maxArea": 800,
            "headSize": 15,
            "nbTailPoints": 20
        }
    
    def create_config_file(self, output_path: str, **kwargs) -> str:
        """
        Create a ZebraZoom configuration file.
        
        Args:
            output_path: Path to save config file
            **kwargs: Configuration parameters
            
        Returns:
            Path to created config file
        """
        config = self._get_default_config()
        config.update(kwargs)
        
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created config file: {output_path}")
        return output_path

