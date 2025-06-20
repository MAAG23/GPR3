import pygame
import numpy as np
import aubio
import sounddevice as sd
import random

# Print available audio devices
print("\nAvailable Audio Input Devices:")
print(sd.query_devices())
default_device = sd.query_devices(kind='input')
print(f"\nDefault Input Device:\n{default_device}")

# Inicialização
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Jogo Tom de Voz")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)
large_font = pygame.font.SysFont(None, 64)

# Variáveis globais
ball_x = 200
ball_y = HEIGHT - 50
ball_target_y = HEIGHT - 50
ball_radius = 20
lives = 3
invulnerable_frames = 0
pitch_detected = False
MIN_PITCH = 40
MAX_PITCH = 400
GROUND_Y = HEIGHT - 50
DESCENT_RESISTANCE = 0.05  # Controls how fast the ball falls
barriers = []
barrier_width = 20
barrier_gap = 150
BASE_BARRIER_SPEED = 3.0  # Renamed from barrier_speed to BASE_BARRIER_SPEED
barrier_speed = BASE_BARRIER_SPEED
barrier_timer = 0
barrier_spawn_interval = 150
score = 0
game_state = "menu"
slowdown_factor = 0.5
normal_speed = 2
SPEED_INCREASE_INTERVAL = 2  # Points needed for each speed increase
SPEED_INCREASE_FACTOR = 1.25  # How much faster it gets each interval
SLOWDOWN_DURATION = 30  # Frames to stay slow (was implicitly 60)
RECOVERY_SPEED = 0.1  # How fast to recover speed

# Pitch detection parameters
samplerate = 44100
win_s = 2048
hop_s = 1024
pitch_o = aubio.pitch("default", win_s, hop_s, samplerate)
pitch_o.set_unit("Hz")
pitch_o.set_silence(-35)  # Less sensitive to quiet sounds
pitch_o.set_tolerance(0.7)  # More strict pitch detection

pitch_history = []
pitch_history_size = 5  # More temporal smoothing

def reset_game():
    global ball_x, ball_y, ball_target_y, lives, invulnerable_frames, barriers, barrier_timer, score, pitch_detected, barrier_speed
    ball_x = 200
    ball_y = HEIGHT - 50
    ball_target_y = HEIGHT - 50
    lives = 3
    invulnerable_frames = 0
    barriers = []
    barrier_timer = 0
    score = 0
    pitch_detected = False
    barrier_speed = BASE_BARRIER_SPEED
    pitch_history.clear()

def update_barrier_speed():
    global barrier_speed, barrier_spawn_interval
    level = score // SPEED_INCREASE_INTERVAL
    if level > 0:
        barrier_speed = BASE_BARRIER_SPEED * (SPEED_INCREASE_FACTOR ** level)
        # Adjust spawn interval to maintain consistent spacing
        barrier_spawn_interval = int(150 / (SPEED_INCREASE_FACTOR ** level))
        # Ensure minimum spawn interval to prevent barriers from being too close
        barrier_spawn_interval = max(30, barrier_spawn_interval)

def audio_callback(indata, frames, time, status):
    global ball_target_y, pitch_detected, pitch_history
    samples = np.frombuffer(indata, dtype=np.float32)
    pitch = pitch_o(samples)[0]
    
    # More focused pitch detection range
    if 80 < pitch < 350:
        pitch_history.append(pitch)
        if len(pitch_history) > pitch_history_size:
            pitch_history.pop(0)
        avg_pitch = sum(pitch_history) / len(pitch_history)

        pitch_detected = True
        relative = ((avg_pitch - MIN_PITCH) / (MAX_PITCH - MIN_PITCH)) ** 0.8
        ball_target_y = int(HEIGHT - relative * (HEIGHT - 50))
        
        print(f"Pitch detected: {avg_pitch:.1f} Hz, Relative height: {relative:.2f}")
    else:
        pitch_detected = False
        pitch_history.clear()
        ball_target_y = GROUND_Y

def add_barrier():
    gap_y = random.randint(100, HEIGHT - 250)
    barriers.append({'x': WIDTH, 'gap_y': gap_y, 'passed': False})

def draw_barriers():
    for b in barriers:
        pygame.draw.rect(screen, (0,255,0), (b['x'], 0, barrier_width, b['gap_y']))
        pygame.draw.rect(screen, (0,255,0), (b['x'], b['gap_y'] + barrier_gap, barrier_width, HEIGHT))

def check_collision():
    global lives, barriers
    for i, b in enumerate(barriers):
        if ball_x + ball_radius > b['x'] and ball_x - ball_radius < b['x'] + barrier_width:
            if not (b['gap_y'] < ball_y < b['gap_y'] + barrier_gap):
                lives -= 1
                # Remove a barreira que causou a colisão
                barriers.pop(i)
                return True
    return False

def recuar_barreiras():
    for b in barriers:
        if b['x'] < ball_x:
            b['x'] += barrier_speed

def draw_lives():
    for i in range(lives):
        pygame.draw.circle(screen, (255, 0, 0), (WIDTH - 30 - i*30, 30), 10)

def draw_pitch_ground():
    pygame.draw.line(screen, (100, 100, 100), (0, GROUND_Y), (WIDTH, GROUND_Y), 2)
    status_text = "Voice Detected!" if pitch_detected else "No Voice Detected"
    color = (0, 255, 0) if pitch_detected else (255, 0, 0)
    text = font.render(status_text, True, color)
    screen.blit(text, (10, GROUND_Y + 5))
    
    if pitch_detected and pitch_history:
        pitch_text = f"Pitch: {sum(pitch_history) / len(pitch_history):.1f} Hz"
        pitch_info = font.render(pitch_text, True, (200, 200, 200))
        screen.blit(pitch_info, (10, GROUND_Y + 35))

def draw_button(text, center):
    rect = pygame.Rect(0, 0, 400, 70)
    rect.center = center
    pygame.draw.rect(screen, (50, 120, 220), rect, border_radius=12)
    label = font.render(text, True, (255, 255, 255))
    screen.blit(label, (rect.centerx - label.get_width()//2, rect.centery - label.get_height()//2))
    return rect

def main_menu():
    screen.fill((10, 10, 30))
    title = large_font.render("Jogos de Voz", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))

    btn1 = draw_button("Desafio de tonalidade", (WIDTH//2, 300))
    btn2 = draw_button("Comando de voz - Brevemente...", (WIDTH//2, 400))
    return btn1, btn2

def game_over_menu():
    screen.fill((20, 0, 20))
    title = large_font.render("Game Over", True, (255, 80, 80))
    score_text = font.render(f"Score: {score}", True, (255,255,255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 230))
    return draw_button("Tentar Novamente", (WIDTH//2, 320))

def new_mode_menu():
    screen.fill((30, 10, 20))
    title = large_font.render("Novo Modo (Em Desenvolvimento)", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
    text = font.render("Este modo ainda está em desenvolvimento.", True, (255, 255, 255))
    screen.blit(text, (WIDTH//2 - text.get_width()//2, 250))
    return draw_button("Voltar ao Menu", (WIDTH//2, 350))

def draw_score():
    score_text = font.render(f"Score: {score}", True, (255,255,255))
    screen.blit(score_text, (10, 10))
    
    # Show current speed level
    level = score // SPEED_INCREASE_INTERVAL
    if level > 0:
        speed_text = font.render(f"Speed: {SPEED_INCREASE_FACTOR ** level:.2f}x", True, (255, 200, 0))
        screen.blit(speed_text, (10, 40))

# ================== LOOP PRINCIPAL ==================

with sd.InputStream(channels=1, callback=audio_callback, samplerate=samplerate, blocksize=hop_s):
    running = True
    while running:
        mouse_clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicked = True

        if game_state == "menu":
            btn1, btn2 = main_menu()
            if mouse_clicked:
                if btn1.collidepoint(pygame.mouse.get_pos()):
                    reset_game()
                    game_state = "playing"
                elif btn2.collidepoint(pygame.mouse.get_pos()):
                    reset_game()
                    game_state = "new_mode"

        elif game_state == "new_mode":
            btn_back = new_mode_menu()
            if mouse_clicked and btn_back.collidepoint(pygame.mouse.get_pos()):
                game_state = "menu"

        elif game_state == "game_over":
            btn = game_over_menu()
            if mouse_clicked and btn.collidepoint(pygame.mouse.get_pos()):
                reset_game()
                game_state = "playing"

        elif game_state == "playing":
            screen.fill((20, 20, 30))

            # Atualizar barreiras
            barrier_timer += 1
            if barrier_timer > barrier_spawn_interval:
                add_barrier()
                barrier_timer = 0
            for b in barriers:
                b['x'] -= barrier_speed
            barriers = [b for b in barriers if b['x'] + barrier_width > 0]

            # Colisão
            if invulnerable_frames == 0 and (check_collision() or ball_y < 0 or ball_y > HEIGHT):
                invulnerable_frames = SLOWDOWN_DURATION
                if lives <= 0:
                    game_state = "game_over"
            elif invulnerable_frames > 0:
                invulnerable_frames -= 1

            # Score and speed update
            for b in barriers:
                if not b['passed'] and b['x'] + barrier_width < ball_x:
                    score += 1
                    b['passed'] = True
                    update_barrier_speed()
                    # Visual feedback when speed increases
                    if score % SPEED_INCREASE_INTERVAL == 0:
                        print(f"Speed increased! Now at {barrier_speed:.2f}")

            if not pitch_detected:
                ball_target_y = GROUND_Y

            # Ball movement with resistance on descent
            if ball_y < ball_target_y:  # Moving down
                ball_y += (ball_target_y - ball_y) * DESCENT_RESISTANCE
            else:  # Moving up - instant response
                ball_y = ball_target_y

            color = (0, 200, 255) if invulnerable_frames == 0 else (100, 100, 255)
            pygame.draw.circle(screen, color, (ball_x, ball_y), ball_radius)

            draw_barriers()
            draw_lives()
            draw_pitch_ground()
            draw_score()

        pygame.display.flip()
        clock.tick(60)

pygame.quit()
