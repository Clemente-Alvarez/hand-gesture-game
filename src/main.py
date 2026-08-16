import ctypes
import math

import sdl3
from PIL import Image, ImageDraw, ImageFont

from hand_tracker import HandTraker


# ============================================================
# CONFIGURACIÓN
# ============================================================

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# True  -> movimiento tipo espejo
# False -> movimiento normal
MIRROR_X = True

# Fotografías que se irán mostrando.
# Cambia estos nombres por tus imágenes.
IMAGE_PATHS = [
    "images/foto1.jpg",
    "images/foto2.jpg",
    "images/foto3.jpg",
]

# Mensaje específico para cada imagen.
SUCCESS_MESSAGES = [
    "¡Muy bien!",
    "¡Muy bien!",
    "¡Muy bien!",
]

# Fuente de Ubuntu. Puedes cambiarla si quieres otra.
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

SUCCESS_FONT_SIZE = 30
SUCCESS_MESSAGE_SECONDS = 3

# El hueco de cada imagen se define en coordenadas de la imagen
# original: (x, y, width, height).
#
# Si una imagen no está en la lista TARGETS, se usa TARGET_DEFAULT.
TARGETS = [
    # x, y, ancho, alto, escala_inicial
    (650, 500, 220, 220, 0.60),
    (300, 250, 220, 180, 0.75),
    (900, 350, 180, 240, 0.50),
]

TARGET_DEFAULT = (0.40, 0.40, 0.15, 0.15, 0.60)
# Si no quieres depender de las dimensiones de cada imagen,
# puedes usar TARGET_DEFAULT como porcentajes:
# (x_relativo, y_relativo, ancho_relativo, alto_relativo, escala_inicial)

# Tolerancias para considerar que la pieza está colocada.
POSITION_TOLERANCE = 35
SCALE_TOLERANCE = 0.18

MIN_SCALE = 0.25
MAX_SCALE = 4.0

# Separación de la pieza respecto al hueco al aparecer.
PIECE_START_OFFSET_X = 180
PIECE_START_OFFSET_Y = 80


# ============================================================
# UTILIDADES
# ============================================================

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def make_texture(renderer, image):
    """
    Convierte una imagen Pillow RGBA en una SDL_Texture.
    """

    image = image.convert("RGBA")

    width, height = image.size
    pixel_data = image.tobytes("raw", "RGBA")

    texture = sdl3.SDL_CreateTexture(
        renderer,
        sdl3.SDL_PIXELFORMAT_RGBA32,
        sdl3.SDL_TEXTUREACCESS_STATIC,
        width,
        height,
    )

    if not texture:
        raise RuntimeError(
            f"No se pudo crear SDL_Texture: "
            f"{sdl3.SDL_GetError()}"
        )

    # SDL necesita un buffer que permanezca válido durante la
    # llamada a SDL_UpdateTexture.
    buffer = ctypes.create_string_buffer(pixel_data)

    if not sdl3.SDL_UpdateTexture(
        texture,
        None,
        buffer,
        width * 4,
    ):
        sdl3.SDL_DestroyTexture(texture)

        raise RuntimeError(
            f"No se pudo actualizar SDL_Texture: "
            f"{sdl3.SDL_GetError()}"
        )

    return texture


def make_text_texture(renderer, text, font_path, font_size):
    """Crea una SDL_Texture RGBA con texto usando Pillow."""

    try:
        font = ImageFont.truetype(font_path, font_size)
    except OSError as error:
        raise RuntimeError(
            f"No se pudo cargar la fuente '{font_path}'. "
            f"Cambia FONT_PATH. Error: {error}"
        )

    dummy = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)

    bbox = draw.textbbox((0, 0), text, font=font)

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    padding = 12

    image = Image.new(
        "RGBA",
        (
            text_width + padding * 2,
            text_height + padding * 2,
        ),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(image)

    # Sombra
    draw.text(
        (padding + 3, padding + 3),
        text,
        font=font,
        fill=(0, 0, 0, 180),
    )

    # Texto
    draw.text(
        (padding, padding),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )

    texture = make_texture(renderer, image)

    if not sdl3.SDL_SetTextureBlendMode(
        texture,
        sdl3.SDL_BLENDMODE_BLEND,
    ):
        sdl3.SDL_DestroyTexture(texture)
        raise RuntimeError(
            f"No se pudo activar el blending del texto: "
            f"{sdl3.SDL_GetError()}"
        )

    return texture, image.size


def draw_texture(renderer, texture, x, y, width, height):
    """
    Dibuja una textura escalada a un SDL_FRect.
    """

    dst = sdl3.SDL_FRect(
        float(x),
        float(y),
        float(width),
        float(height),
    )

    sdl3.SDL_RenderTexture(
        renderer,
        texture,
        None,
        ctypes.byref(dst),
    )


# ============================================================
# PUZZLE
# ============================================================

class Puzzle:

    def __init__(self, renderer, image_paths):
        self.renderer = renderer
        self.image_paths = image_paths

        self.image_index = 0

        self.background_texture = None
        self.piece_texture = None

        self.image_width = 0
        self.image_height = 0

        # Rectángulo del hueco en coordenadas de la imagen.
        self.target_x = 0
        self.target_y = 0
        self.target_width = 0
        self.target_height = 0

        # Escala con la que aparece inicialmente la pieza.
        self.initial_piece_scale = 1.0

        # Transformación imagen -> pantalla.
        self.display_x = 0
        self.display_y = 0
        self.display_width = 0
        self.display_height = 0
        self.display_scale = 1.0

        # Pieza en coordenadas de pantalla.
        self.piece_x = 0
        self.piece_y = 0

        # Escala de la pieza respecto a su tamaño original.
        self.piece_scale = 1.0

        # Estado de interacción.
        self.moving = False
        self.scaling = False

        self.move_offset_x = 0
        self.move_offset_y = 0

        self.initial_distance = 0
        self.initial_scale = 1.0

        self.completed = False

        # Estado del mensaje de éxito.
        self.success_message = ""
        self.success_texture = None
        self.success_texture_width = 0
        self.success_texture_height = 0
        self.success_until = 0

        self.load_current_image()

    # --------------------------------------------------------
    # Carga de una fotografía
    # --------------------------------------------------------

    def load_current_image(self):

        self.destroy_textures()

        image_path = self.image_paths[self.image_index]

        print(f"Cargando imagen: {image_path}")

        image = Image.open(image_path).convert("RGBA")

        self.image_width, self.image_height = image.size

        print(
            f"Resolución: "
            f"{self.image_width}x{self.image_height}"
        )

        # ----------------------------------------------------
        # Hueco
        # ----------------------------------------------------

        if self.image_index < len(TARGETS):
            target = TARGETS[self.image_index]

            self.target_x = int(target[0])
            self.target_y = int(target[1])
            self.target_width = int(target[2])
            self.target_height = int(target[3])
            self.initial_piece_scale = float(target[4])

        else:
            self.target_x = int(
                self.image_width * TARGET_DEFAULT[0]
            )

            self.target_y = int(
                self.image_height * TARGET_DEFAULT[1]
            )

            self.target_width = int(
                self.image_width * TARGET_DEFAULT[2]
            )

            self.target_height = int(
                self.image_height * TARGET_DEFAULT[3]
            )
            self.initial_piece_scale = float(TARGET_DEFAULT[4])

        # Asegurarnos de que el rectángulo está dentro de la foto.
        self.target_x = clamp(
            self.target_x,
            0,
            max(0, self.image_width - 1),
        )

        self.target_y = clamp(
            self.target_y,
            0,
            max(0, self.image_height - 1),
        )

        self.target_width = min(
            self.target_width,
            self.image_width - self.target_x,
        )

        self.target_height = min(
            self.target_height,
            self.image_height - self.target_y,
        )

        # ----------------------------------------------------
        # Crear textura de fondo
        # ----------------------------------------------------

        self.background_texture = make_texture(
            self.renderer,
            image,
        )

        # ----------------------------------------------------
        # Recortar la pieza
        # ----------------------------------------------------

        piece = image.crop(
            (
                self.target_x,
                self.target_y,
                self.target_x + self.target_width,
                self.target_y + self.target_height,
            )
        )

        self.piece_texture = make_texture(
            self.renderer,
            piece,
        )

        # ----------------------------------------------------
        # Calcular cómo se muestra la imagen manteniendo ratio
        # ----------------------------------------------------

        scale_x = WINDOW_WIDTH / self.image_width
        scale_y = WINDOW_HEIGHT / self.image_height

        self.display_scale = min(scale_x, scale_y)

        self.display_width = (
            self.image_width * self.display_scale
        )

        self.display_height = (
            self.image_height * self.display_scale
        )

        self.display_x = (
            WINDOW_WIDTH - self.display_width
        ) / 2

        self.display_y = (
            WINDOW_HEIGHT - self.display_height
        ) / 2

        # ----------------------------------------------------
        # Posición inicial de la pieza
        # ----------------------------------------------------

        target_screen_x, target_screen_y = (
            self.image_to_screen(
                self.target_x,
                self.target_y,
            )
        )

        target_screen_w = (
            self.target_width *
            self.display_scale
        )

        target_screen_h = (
            self.target_height *
            self.display_scale
        )

        # Aparece fuera del hueco.
        self.piece_x = (
            target_screen_x +
            target_screen_w / 2 +
            PIECE_START_OFFSET_X
        )

        self.piece_y = (
            target_screen_y +
            target_screen_h / 2 +
            PIECE_START_OFFSET_Y
        )

        # Escala inicial configurada para esta pieza.
        self.piece_scale = clamp(
            self.initial_piece_scale,
            MIN_SCALE,
            MAX_SCALE,
        )

        # Mensaje correspondiente a esta fotografía.
        if self.image_index < len(SUCCESS_MESSAGES):
            self.success_message = SUCCESS_MESSAGES[self.image_index]
        else:
            self.success_message = "¡Imagen completada!"

        self.success_texture = None
        self.success_texture_width = 0
        self.success_texture_height = 0
        self.success_until = 0

        self.moving = False
        self.scaling = False
        self.completed = False

    # --------------------------------------------------------
    # Transformaciones
    # --------------------------------------------------------

    def image_to_screen(self, image_x, image_y):

        screen_x = (
            self.display_x +
            image_x * self.display_scale
        )

        screen_y = (
            self.display_y +
            image_y * self.display_scale
        )

        return screen_x, screen_y

    def target_center_screen(self):

        center_x = (
            self.target_x +
            self.target_width / 2
        )

        center_y = (
            self.target_y +
            self.target_height / 2
        )

        return self.image_to_screen(
            center_x,
            center_y,
        )

    def piece_size_screen(self):

        width = (
            self.target_width *
            self.display_scale *
            self.piece_scale
        )

        height = (
            self.target_height *
            self.display_scale *
            self.piece_scale
        )

        return width, height

    # --------------------------------------------------------
    # Actualizar interacción
    # --------------------------------------------------------

    def update(self, hands):

        if self.completed:
            return

        # ----------------------------------------------------
        # Obtener manos haciendo pinch
        # ----------------------------------------------------

        pinches = []

        for hand in hands:

            if not hand["pinch"]:
                continue

            x = hand["x"]
            y = hand["y"]

            if MIRROR_X:
                x = 1.0 - x

            screen_x = x * WINDOW_WIDTH
            screen_y = y * WINDOW_HEIGHT

            pinches.append(
                (screen_x, screen_y)
            )

        # ----------------------------------------------------
        # DOS PINCHES -> ESCALAR
        # ----------------------------------------------------

        if len(pinches) >= 2:

            p1 = pinches[0]
            p2 = pinches[1]

            current_distance = distance(
                p1[0],
                p1[1],
                p2[0],
                p2[1],
            )

            if not self.scaling:

                self.scaling = True

                self.initial_distance = (
                    current_distance
                )

                self.initial_scale = (
                    self.piece_scale
                )

            if self.initial_distance > 0:

                self.piece_scale = (
                    self.initial_scale *
                    current_distance /
                    self.initial_distance
                )

                self.piece_scale = clamp(
                    self.piece_scale,
                    MIN_SCALE,
                    MAX_SCALE,
                )

            # El centro de la pieza sigue el centro
            # entre las dos manos.
            self.piece_x = (
                p1[0] + p2[0]
            ) / 2

            self.piece_y = (
                p1[1] + p2[1]
            ) / 2

            self.moving = False

        # ----------------------------------------------------
        # UN PINCH -> MOVER
        # ----------------------------------------------------

        elif len(pinches) == 1:

            pinch_x, pinch_y = pinches[0]

            if not self.moving:

                self.moving = True

                self.move_offset_x = (
                    self.piece_x - pinch_x
                )

                self.move_offset_y = (
                    self.piece_y - pinch_y
                )

            self.piece_x = (
                pinch_x +
                self.move_offset_x
            )

            self.piece_y = (
                pinch_y +
                self.move_offset_y
            )

            self.scaling = False

        # ----------------------------------------------------
        # NINGÚN PINCH
        # ----------------------------------------------------

        else:

            # Si acaba de terminar un movimiento,
            # comprobamos si la pieza está colocada.
            if self.moving or self.scaling:

                self.check_solution()

            self.moving = False
            self.scaling = False

    # --------------------------------------------------------
    # Comprobar solución
    # --------------------------------------------------------

    def check_solution(self):

        target_x, target_y = (
            self.target_center_screen()
        )

        # Distancia entre centros.
        position_error = distance(
            self.piece_x,
            self.piece_y,
            target_x,
            target_y,
        )

        # Error de escala.
        scale_error = abs(
            self.piece_scale - 1.0
        )

        print(
            f"Posición: {position_error:.1f}px | "
            f"Escala: {self.piece_scale:.2f}"
        )

        if (
            position_error <= POSITION_TOLERANCE
            and
            scale_error <= SCALE_TOLERANCE
        ):

            print("¡Puzzle completado!")
            print(f"Mensaje: {self.success_message}")

            # Encajamos exactamente la pieza.
            self.piece_x = target_x
            self.piece_y = target_y
            self.piece_scale = 1.0

            # Crear el texto una sola vez al completar.
            if self.success_texture is None:
                (
                    self.success_texture,
                    (
                        self.success_texture_width,
                        self.success_texture_height,
                    ),
                ) = make_text_texture(
                    self.renderer,
                    self.success_message,
                    FONT_PATH,
                    SUCCESS_FONT_SIZE,
                )

            self.success_until = (
                sdl3.SDL_GetTicks()
                + int(SUCCESS_MESSAGE_SECONDS * 1000)
            )

            self.completed = True

    # --------------------------------------------------------
    # Render
    # --------------------------------------------------------

    def render(self, renderer):

        # ----------------------------------------------------
        # Fondo
        # ----------------------------------------------------

        draw_texture(
            renderer,
            self.background_texture,
            self.display_x,
            self.display_y,
            self.display_width,
            self.display_height,
        )

        # ----------------------------------------------------
        # Dibujar el hueco
        # ----------------------------------------------------

        target_x, target_y = (
            self.image_to_screen(
                self.target_x,
                self.target_y,
            )
        )

        target_w = (
            self.target_width *
            self.display_scale
        )

        target_h = (
            self.target_height *
            self.display_scale
        )

        # Oscurecer el hueco.
        sdl3.SDL_SetRenderDrawColor(
            renderer,
            20,
            20,
            20,
            220,
        )

        hole_rect = sdl3.SDL_FRect(
            float(target_x),
            float(target_y),
            float(target_w),
            float(target_h),
        )

        sdl3.SDL_RenderFillRect(
            renderer,
            ctypes.byref(hole_rect),
        )

        # Borde del hueco.
        sdl3.SDL_SetRenderDrawColor(
            renderer,
            255,
            255,
            255,
            255,
        )

        sdl3.SDL_RenderRect(
            renderer,
            ctypes.byref(hole_rect),
        )

        # ----------------------------------------------------
        # Pieza
        # ----------------------------------------------------

        piece_w, piece_h = (
            self.piece_size_screen()
        )

        piece_x = (
            self.piece_x -
            piece_w / 2
        )

        piece_y = (
            self.piece_y -
            piece_h / 2
        )

        draw_texture(
            renderer,
            self.piece_texture,
            piece_x,
            piece_y,
            piece_w,
            piece_h,
        )

        # Borde de la pieza.
        sdl3.SDL_SetRenderDrawColor(
            renderer,
            255,
            255,
            255,
            255,
        )

        piece_rect = sdl3.SDL_FRect(
            float(piece_x),
            float(piece_y),
            float(piece_w),
            float(piece_h),
        )

        sdl3.SDL_RenderRect(
            renderer,
            ctypes.byref(piece_rect),
        )

        # ----------------------------------------------------
        # Mensaje de éxito
        # ----------------------------------------------------

        if (
            self.completed
            and self.success_texture is not None
            and sdl3.SDL_GetTicks() < self.success_until
        ):

            panel_width = self.success_texture_width + 50
            panel_height = self.success_texture_height + 30

            panel_x = (WINDOW_WIDTH - panel_width) / 2
            panel_y = 35

            sdl3.SDL_SetRenderDrawColor(
                renderer,
                0,
                0,
                0,
                210,
            )

            panel = sdl3.SDL_FRect(
                float(panel_x),
                float(panel_y),
                float(panel_width),
                float(panel_height),
            )

            sdl3.SDL_RenderFillRect(
                renderer,
                ctypes.byref(panel),
            )

            text_x = (
                WINDOW_WIDTH - self.success_texture_width
            ) / 2

            text_y = (
                panel_y
                + (panel_height - self.success_texture_height) / 2
            )

            draw_texture(
                renderer,
                self.success_texture,
                text_x,
                text_y,
                self.success_texture_width,
                self.success_texture_height,
            )

    # --------------------------------------------------------
    # Siguiente imagen
    # --------------------------------------------------------

    def next_image(self):

        self.image_index += 1

        if self.image_index >= len(self.image_paths):

            print("¡Has completado todas las imágenes!")

            self.image_index = 0

        self.load_current_image()

    # --------------------------------------------------------
    # Limpieza
    # --------------------------------------------------------

    def destroy_textures(self):

        if self.background_texture:

            sdl3.SDL_DestroyTexture(
                self.background_texture
            )

            self.background_texture = None

        if self.piece_texture:

            sdl3.SDL_DestroyTexture(
                self.piece_texture
            )

            self.piece_texture = None

        if self.success_texture:

            sdl3.SDL_DestroyTexture(
                self.success_texture
            )

            self.success_texture = None

    def close(self):

        self.destroy_textures()


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # SDL
    # --------------------------------------------------------

    if not sdl3.SDL_Init(
        sdl3.SDL_INIT_VIDEO
    ):

        print(
            "Error inicializando SDL:",
            sdl3.SDL_GetError(),
        )

        return

    window = sdl3.SDL_CreateWindow(
        b"Hand Tracking Puzzle",
        WINDOW_WIDTH,
        WINDOW_HEIGHT,
        0,
    )

    if not window:

        print(
            "Error creando ventana:",
            sdl3.SDL_GetError(),
        )

        sdl3.SDL_Quit()

        return

    renderer = sdl3.SDL_CreateRenderer(
        window,
        None,
    )

    if not renderer:

        print(
            "Error creando renderer:",
            sdl3.SDL_GetError(),
        )

        sdl3.SDL_DestroyWindow(window)
        sdl3.SDL_Quit()

        return

    # --------------------------------------------------------
    # MediaPipe
    # --------------------------------------------------------

    tracker = HandTraker()

    # --------------------------------------------------------
    # Puzzle
    # --------------------------------------------------------

    try:

        puzzle = Puzzle(
            renderer,
            IMAGE_PATHS,
        )

    except Exception as error:

        print(
            f"Error cargando el puzzle: {error}"
        )

        tracker.close()

        sdl3.SDL_DestroyRenderer(renderer)
        sdl3.SDL_DestroyWindow(window)
        sdl3.SDL_Quit()

        return

    # --------------------------------------------------------
    # Bucle
    # --------------------------------------------------------

    running = True

    event = sdl3.SDL_Event()

    while running:

        # ----------------------------------------------------
        # Eventos SDL
        # ----------------------------------------------------

        while sdl3.SDL_PollEvent(
            ctypes.byref(event)
        ):

            if event.type == sdl3.SDL_EVENT_QUIT:

                running = False

        # ----------------------------------------------------
        # MediaPipe
        # ----------------------------------------------------

        tracker.loop()

        hands = tracker.get_hands()

        # ----------------------------------------------------
        # Puzzle
        # ----------------------------------------------------

        puzzle.update(hands)

        # ----------------------------------------------------
        # Render
        # ----------------------------------------------------

        sdl3.SDL_SetRenderDrawColor(
            renderer,
            15,
            15,
            15,
            255,
        )

        sdl3.SDL_RenderClear(renderer)

        puzzle.render(renderer)

        sdl3.SDL_RenderPresent(renderer)

        # ----------------------------------------------------
        # Si se completó, pasar a la siguiente imagen
        # ----------------------------------------------------

        if puzzle.completed:

            # Mostrar el mensaje durante el tiempo configurado
            # y después pasar a la siguiente fotografía.
            if sdl3.SDL_GetTicks() >= puzzle.success_until:
                puzzle.next_image()

    # --------------------------------------------------------
    # Limpieza
    # --------------------------------------------------------

    puzzle.close()
    tracker.close()

    sdl3.SDL_DestroyRenderer(renderer)
    sdl3.SDL_DestroyWindow(window)

    sdl3.SDL_Quit()


if __name__ == "__main__":
    main()
