import pygame
import numpy as np
import wave
import pyaudio
import threading
import sys
import cv2
import tkinter as tk
from tkinter import filedialog, colorchooser

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
TOPBAR_HEIGHT = 40
BAR_WIDTH = 20
NUM_BARS = WIDTH // (BAR_WIDTH + 5)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Music Reactive Bars with Video")

# Default settings
color = (30, 144, 255)  # Default Dodger Blue
audio_signal = None
audio_data = None
frame_rate = 44100
num_channels = 1
sample_width = 2
frame_idx = 0
audio_finished = True
playing = False
audio_idx = 0

# Video settings
video_path = None
video_cap = None
video_frame = None
video_playing = False


# Load and process audio
def load_audio(file_path):
    global audio_signal, frame_rate, num_channels, sample_width, audio_data, audio_finished, frame_idx, playing, audio_idx

    wave_file = wave.open(file_path, 'rb')
    frame_rate = wave_file.getframerate()
    num_frames = wave_file.getnframes()
    num_channels = wave_file.getnchannels()
    sample_width = wave_file.getsampwidth()

    wave_file.rewind()
    audio_data = wave_file.readframes(num_frames)
    wave_file.close()

    audio_signal = np.frombuffer(audio_data, dtype=np.int16)
    if num_channels == 2:
        audio_signal = audio_signal[::2]

    audio_signal = audio_signal / np.max(np.abs(audio_signal))

    audio_finished = False
    frame_idx = 0
    audio_idx = 0  # Reset audio position
    playing = True
    threading.Thread(target=play_audio, daemon=True).start()


# Play audio
def play_audio():
    global audio_finished, playing, audio_idx

    if audio_data is None:
        return

    pa = pyaudio.PyAudio()
    stream = pa.open(format=pa.get_format_from_width(sample_width),
                     channels=num_channels,
                     rate=frame_rate,
                     output=True)

    chunk_size = 1024

    while audio_idx < len(audio_data):
        if not playing:
            break  # Stop if paused

        chunk = audio_data[audio_idx:audio_idx + chunk_size]

        if len(chunk) == 0:
            break

        stream.write(chunk)
        audio_idx += chunk_size  # Correctly move forward in buffer

    stream.stop_stream()
    stream.close()
    pa.terminate()
    audio_finished = audio_idx >= len(audio_data)


# Select and load new audio file
def select_new_audio():
    file_path = filedialog.askopenfilename(filetypes=[("WAV Files", "*.wav")])
    if file_path:
        load_audio(file_path)


# Select and load video file
def select_new_video():
    global video_path, video_cap, video_playing

    file_path = filedialog.askopenfilename(filetypes=[("MP4 Files", "*.mp4"), ("AVI Files", "*.avi")])
    if file_path:
        video_path = file_path
        video_cap = cv2.VideoCapture(video_path)
        video_playing = True


# Toggle play/pause
def toggle_play_pause():
    global playing, audio_idx

    if audio_data is None:
        return

    playing = not playing  # Toggle state

    if playing and not audio_finished:
        threading.Thread(target=play_audio, daemon=True).start()  # Resume


# Pick bar color
def pick_color():
    global color
    rgb, _ = colorchooser.askcolor()
    if rgb:
        color = tuple(map(int, rgb))


# Get video frame
def get_video_frame():
    global video_cap, video_frame

    if video_cap and video_cap.isOpened():
        ret, frame = video_cap.read()
        if not ret:
            video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop video
            ret, frame = video_cap.read()

        if ret:
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.rot90(frame)  # Rotate 90 degrees counterclockwise
            frame = np.flipud(frame)  # Flip vertically to correct orientation

            video_frame = pygame.surfarray.make_surface(frame)

        return video_frame
    return None
 

# Pygame loop
running = True
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)
credit_font = pygame.font.Font(None, 20)

button_width, button_height = 100, 30
upload_audio_button = pygame.Rect(10, 5, button_width, button_height)
upload_video_button = pygame.Rect(120, 5, button_width, button_height)
play_pause_button = pygame.Rect(230, 5, button_width, button_height)
color_picker_button = pygame.Rect(340, 5, button_width, button_height)
quit_button = pygame.Rect(450, 5, button_width, button_height)

while running:
    screen.fill((0, 0, 0))

    # Draw Video Background
    if video_playing:
        frame_surface = get_video_frame()
        if frame_surface:
            frame_surface.set_alpha(128)  # Set transparency (faded effect)
            screen.blit(frame_surface, (0, 0))

    pygame.draw.rect(screen, 'black', (0, 0, WIDTH, TOPBAR_HEIGHT))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if upload_audio_button.collidepoint(event.pos):
                select_new_audio()
            elif upload_video_button.collidepoint(event.pos):
                select_new_video()
            elif play_pause_button.collidepoint(event.pos):
                toggle_play_pause()
            elif color_picker_button.collidepoint(event.pos):
                pick_color()
            elif quit_button.collidepoint(event.pos):
                pygame.quit()
                sys.exit()

    # Update visualization
    if audio_signal is not None and playing:
        if frame_idx < len(audio_signal) - NUM_BARS:
            amplitudes = np.abs(audio_signal[frame_idx:frame_idx+NUM_BARS]) * 200
            frame_idx += int(frame_rate / 60)
        else:
            audio_finished = True
            amplitudes = np.zeros(NUM_BARS)

        for i in range(NUM_BARS):
            bar_height = int(amplitudes[i])
            pygame.draw.rect(screen, color, (i * (BAR_WIDTH + 5), HEIGHT - bar_height, BAR_WIDTH, bar_height))

    # Draw buttons
    pygame.draw.rect(screen, "black", upload_audio_button)
    pygame.draw.rect(screen, "black", upload_video_button)
    pygame.draw.rect(screen, "black", play_pause_button)
    pygame.draw.rect(screen, "black", color_picker_button)
    pygame.draw.rect(screen, "black", quit_button)

    upload_audio_text = font.render("Upload Audio", True, (255, 255, 255))
    upload_video_text = font.render("Upload Video", True, (255, 255, 255))
    play_pause_text = font.render("Play/Pause", True, (255, 255, 255))
    color_text = font.render("Color", True, (255, 255, 255))
    quit_text = font.render("Quit", True, (255, 255, 255))

    screen.blit(upload_audio_text, (15, 10))
    screen.blit(upload_video_text, (125, 10))
    screen.blit(play_pause_text, (235, 10))
    screen.blit(color_text, (360, 10))
    screen.blit(quit_text, (470, 10))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
