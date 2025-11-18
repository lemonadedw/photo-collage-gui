import sys
import os
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QSizePolicy, QComboBox
)
from PyQt6.QtGui import QPixmap, QIcon, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QStandardPaths
from PIL import ImageQt
from photo_collage import create_collage

icon_path = './src/icon.png'
if not os.path.exists(icon_path):
    print(f"Icon file not found: {icon_path}")
else:
    print(f"Icon file found: {icon_path}")


class CollageWorker(QThread):
    collage_created = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, folder_path, size_value, dimension):
        super().__init__()
        self.folder_path = folder_path
        self.size_value = size_value
        self.dimension = dimension

    def run(self):
        try:
            collage = create_collage(
                self.folder_path, self.size_value, self.dimension)
            self.collage_created.emit(collage)
        except Exception as e:
            self.error_occurred.emit(str(e))


class PhotoCollageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Collage Creator")
        self.init_ui()
        # Apply small platform-specific tweaks (sizes, fonts) for a more native feel
        try:
            self.apply_platform_tweaks()
        except Exception:
            # Non-critical: keep running even if tweaks fail
            pass
        self.generated_collage = None
        self.check_default_folder()
        self.initial_resize_done = False

    def apply_platform_tweaks(self):
        """Apply platform-specific UI tweaks to make controls feel more native.

        On macOS this will increase button heights, use the system font hint,
        and enable unified title/toolbars where available.
        """
        if sys.platform != "darwin":
            return

        # Enable high-DPI pixmaps and scaling (better on Retina displays)
        QApplication.setAttribute(
            Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        QApplication.setAttribute(
            Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)

        # Set a system-like font size/hint so controls size match platform expectations
        font = self.font() or QFont()
        font.setPointSize(max(12, font.pointSize()))
        font.setStyleHint(QFont.StyleHint.System)
        QApplication.instance().setFont(font)

        # Use unified title/tool bar appearance on macOS where available
        try:
            self.setUnifiedTitleAndToolBarOnMac(True)
        except Exception:
            pass

        # Tweak buttons: slightly taller and small padding so they feel mac-like
        for btn in self.main_widget.findChildren(QPushButton):
            try:
                btn.setMinimumHeight(28)
                # avoid forcing heavy stylesheet; add only minimal padding
                existing = btn.styleSheet() or ""
                if "padding" not in existing:
                    btn.setStyleSheet(existing + "padding:6px 12px;")
            except Exception:
                continue

    def init_ui(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        self.setup_folder_selection()
        self.setup_output_path()
        self.setup_resolution()
        self.setup_labels()
        self.setup_buttons()
        self.setup_preview_frame()

    def setup_folder_selection(self):
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Select Image Folder:"))
        default_pictures_path = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.PicturesLocation)
        self.folder_path = QLineEdit(
            os.path.join(default_pictures_path, 'images'))
        folder_layout.addWidget(self.folder_path)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_folder)
        folder_layout.addWidget(browse_button)
        self.layout.addLayout(folder_layout)

    def setup_output_path(self):
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Path:"))
        default_pictures_path = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.PicturesLocation)
        self.output_path = QLineEdit(os.path.join(
            default_pictures_path, 'collage.jpg'))
        output_layout.addWidget(self.output_path)
        output_browse_button = QPushButton("Browse")
        output_browse_button.clicked.connect(self.browse_output_path)
        output_layout.addWidget(output_browse_button)
        self.layout.addLayout(output_layout)

    def setup_resolution(self):
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(
            QLabel("Resolution of each small picture:"))
        self.size_dropdown = QComboBox(self)
        self.size_dropdown.addItems([str(i) for i in range(100, 1100, 100)])
        self.size_dropdown.setCurrentIndex(3)
        self.size_dropdown.currentIndexChanged.connect(
            self.update_final_size_label)
        resolution_layout.addWidget(self.size_dropdown)
        self.layout.addLayout(resolution_layout)

    def setup_labels(self):
        labels_layout = QVBoxLayout()
        self.dimension_label = QLabel("No valid directory selected yet.")
        labels_layout.addWidget(self.dimension_label)
        self.final_size_label = QLabel("Final collage size: Unknown")
        labels_layout.addWidget(self.final_size_label)
        self.layout.addLayout(labels_layout)

    def setup_buttons(self):
        buttons_layout = QHBoxLayout()
        self.create_button = QPushButton("Generate Preview")
        self.create_button.clicked.connect(self.preview_collage)
        buttons_layout.addWidget(self.create_button)
        self.save_button = QPushButton("Save Collage")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_collage)
        buttons_layout.addWidget(self.save_button)
        self.layout.addLayout(buttons_layout)

    def setup_preview_frame(self):
        preview_layout = QHBoxLayout()
        self.preview_label = QLabel()
        self.preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setMinimumSize(600, 600)
        placeholder_pixmap = QPixmap(600, 600)
        placeholder_pixmap.fill(Qt.GlobalColor.lightGray)
        self.preview_label.setPixmap(placeholder_pixmap)

        preview_layout.addStretch()
        preview_layout.addWidget(self.preview_label)
        preview_layout.addStretch()
        self.layout.addLayout(preview_layout)

    def check_default_folder(self):
        default_folder = self.folder_path.text()
        if os.path.isdir(default_folder):
            self.update_dimension_label(default_folder)

    def browse_folder(self):
        folder_selected = QFileDialog.getExistingDirectory(
            self, "Select Folder")
        if folder_selected:
            self.folder_path.setText(folder_selected)
            self.update_dimension_label(folder_selected)

    def browse_output_path(self):
        file_selected, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "JPEG files (*.jpg);;All files (*)"
        )
        if file_selected:
            self.output_path.setText(file_selected)

    def update_dimension_label(self, folder_path):
        valid_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
        images = [f for f in os.listdir(
            folder_path) if f.lower().endswith(valid_extensions)]
        num_images = len(images)

        if num_images == 0:
            self.dimension_label.setText(
                "No images found in this folder. Please select a different folder.")
            self.dimension = None
            self.final_size_label.setText("Final collage size: Unknown")
            self.create_button.setEnabled(False)
            return

        dim = int(math.isqrt(num_images))
        if dim * dim == num_images:
            self.dimension = dim
            self.dimension_label.setText(
                f"{dim} x {dim} collage ({num_images} images)")
            self.update_final_size_label()
            self.create_button.setEnabled(True)
        else:
            self.dimension = None
            self.dimension_label.setText(
                f"Cannot use this folder. {num_images} images found, which is not a perfect square.")
            self.final_size_label.setText("Final collage size: Unknown")
            self.create_button.setEnabled(False)

    def update_final_size_label(self):
        if self.dimension is not None:
            try:
                size_value = int(self.size_dropdown.currentText())
                final_size = size_value * self.dimension
                self.final_size_label.setText(
                    f"Final collage size: {final_size} x {final_size}")
            except ValueError:
                self.final_size_label.setText("Invalid resolution entry.")

    def preview_collage(self):
        folder_path = self.folder_path.text()
        if not os.path.exists(folder_path):
            QMessageBox.critical(
                self, "Error", "The selected folder does not exist.")
            return
        if self.dimension is None:
            QMessageBox.critical(
                self, "Error", "Please select a valid folder with a perfect square number of images.")
            return

        size_value = int(self.size_dropdown.currentText())
        self.worker = CollageWorker(folder_path, size_value, self.dimension)
        self.worker.collage_created.connect(self.on_collage_created)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.started.connect(self.on_worker_started)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    @pyqtSlot()
    def on_worker_started(self):
        self.create_button.setText("Generating...")
        self.create_button.setEnabled(False)
        self.save_button.setEnabled(False)

    @pyqtSlot()
    def on_worker_finished(self):
        self.create_button.setText("Generate Preview")
        self.create_button.setEnabled(True)
        self.save_button.setEnabled(True)

    @pyqtSlot(object)
    def on_collage_created(self, collage):
        self.generated_collage = collage
        preview_image = QPixmap.fromImage(ImageQt.ImageQt(collage)).scaled(
            self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio)
        self.preview_label.setPixmap(preview_image)

    @pyqtSlot(str)
    def on_error_occurred(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def save_collage(self):
        if self.generated_collage is None:
            QMessageBox.critical(
                self, "Error", "No collage to save. Generate a preview first.")
            return
        try:
            self.generated_collage.save(
                self.output_path.text(), dpi=(300, 300))
            QMessageBox.information(
                self, "Success", f"Collage saved to {self.output_path.text()}!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def resizeEvent(self, event):
        if not self.initial_resize_done:
            self.setFixedSize(self.size())
            self.initial_resize_done = True
        super().resizeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path))
    window = PhotoCollageApp()
    window.show()
    sys.exit(app.exec())
