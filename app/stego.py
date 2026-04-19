import struct
from io import BytesIO
from typing import List, Tuple

from PIL import Image


MAGIC = b"STEGO1"


class StegoError(Exception):
    pass


def _bytes_to_bits(data: bytes) -> List[int]:
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_bytes(bits: List[int]) -> bytes:
    if len(bits) % 8 != 0:
        raise StegoError("Bit stream length is not divisible by 8.")

    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i:i + 8]:
            byte = (byte << 1) | bit
        out.append(byte)
    return bytes(out)


def _build_payload(secret: bytes, secret_name: str) -> bytes:
    name_bytes = secret_name.encode("utf-8")
    if len(name_bytes) > 65535:
        raise StegoError("Filename too long.")

    return (
        MAGIC
        + struct.pack(">H", len(name_bytes))
        + name_bytes
        + struct.pack(">I", len(secret))
        + secret
    )


def _parse_payload(data: bytes) -> Tuple[str, bytes]:
    if not data.startswith(MAGIC):
        raise StegoError("No valid payload detected. Check S, L, and mode.")

    idx = len(MAGIC)

    if idx + 2 > len(data):
        raise StegoError("Payload header is incomplete.")
    name_len = struct.unpack(">H", data[idx:idx + 2])[0]
    idx += 2

    if idx + name_len > len(data):
        raise StegoError("Payload filename is incomplete.")
    name = data[idx:idx + name_len].decode("utf-8")
    idx += name_len

    if idx + 4 > len(data):
        raise StegoError("Payload length field is incomplete.")
    payload_len = struct.unpack(">I", data[idx:idx + 4])[0]
    idx += 4

    if idx + payload_len > len(data):
        raise StegoError("Payload body is incomplete.")
    payload = data[idx:idx + payload_len]

    return name, payload


def _get_step(step_index: int, base_l: int, mode: str) -> int:
    if mode == "fixed":
        return base_l
    if mode == "cycle":
        cycle = [base_l, base_l * 2, base_l * 3 + 4]
        return cycle[step_index % len(cycle)]
    if mode == "increment":
        return base_l + step_index
    raise StegoError("Unsupported mode. Use fixed, cycle, or increment.")


def _next_positions(total_bits: int, start_bit: int, base_l: int, mode: str, needed_bits: int) -> List[int]:
    if start_bit < 0:
        raise StegoError("S must be non-negative.")
    if base_l <= 0:
        raise StegoError("L must be positive.")

    positions = []
    pos = start_bit
    step_index = 0

    while pos < total_bits and len(positions) < needed_bits:
        positions.append(pos)
        step = _get_step(step_index, base_l, mode)
        pos += step
        step_index += 1

    if len(positions) < needed_bits:
        raise StegoError("Carrier file is too small for the selected message and parameters.")

    return positions


def embed_payload_into_carrier(
    carrier: bytes,
    secret: bytes,
    start_bit: int,
    base_l: int,
    mode: str,
    secret_name: str,
) -> bytes:
    try:
        img = Image.open(BytesIO(carrier))
    except Exception:
        raise StegoError("Carrier must be a valid image file.")

    img = img.convert("RGB")
    pixel_bytes = bytearray(img.tobytes())

    payload = _build_payload(secret, secret_name)
    payload_bits = _bytes_to_bits(payload)

    total_bits = len(pixel_bytes) * 8
    positions = _next_positions(total_bits, start_bit, base_l, mode, len(payload_bits))

    for bit, pos in zip(payload_bits, positions):
        byte_index = pos // 8
        bit_index = 7 - (pos % 8)

        if bit == 1:
            pixel_bytes[byte_index] |= (1 << bit_index)
        else:
            pixel_bytes[byte_index] &= ~(1 << bit_index)

    stego_img = Image.frombytes("RGB", img.size, bytes(pixel_bytes))
    output = BytesIO()
    stego_img.save(output, format="PNG")
    return output.getvalue()


def extract_payload_from_carrier(
    carrier: bytes,
    start_bit: int,
    base_l: int,
    mode: str,
) -> Tuple[str, bytes]:
    try:
        img = Image.open(BytesIO(carrier))
    except Exception:
        raise StegoError("Stego file must be a valid image file.")

    img = img.convert("RGB")
    pixel_bytes = img.tobytes()
    total_bits = len(pixel_bytes) * 8

    extracted_bits = []
    pos = start_bit
    step_index = 0

    while pos < total_bits:
        byte_index = pos // 8
        bit_index = 7 - (pos % 8)
        extracted_bits.append((pixel_bytes[byte_index] >> bit_index) & 1)

        step = _get_step(step_index, base_l, mode)
        pos += step
        step_index += 1

    usable_length = len(extracted_bits) - (len(extracted_bits) % 8)
    extracted_bytes = _bits_to_bytes(extracted_bits[:usable_length])

    return _parse_payload(extracted_bytes)