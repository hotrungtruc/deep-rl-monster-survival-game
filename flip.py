from PIL import Image, ImageSequence

def flip_gif(input_path, output_path, mode="horizontal"):
    # Mở file GIF gốc
    gif = Image.open(input_path)

    # Tạo list chứa các frame đã lật
    frames = []

    # Duyệt từng frame trong ảnh GIF
    for frame in ImageSequence.Iterator(gif):
        # Chuyển frame sang RGB (nếu có alpha)
        frame = frame.convert("RGBA")

        # Lật ảnh
        if mode == "horizontal":
            flipped = frame.transpose(Image.FLIP_LEFT_RIGHT)
        elif mode == "vertical":
            flipped = frame.transpose(Image.FLIP_TOP_BOTTOM)
        else:
            raise ValueError("mode phải là 'horizontal' hoặc 'vertical'")

        # Thêm frame vào list
        frames.append(flipped)

    # Lưu lại GIF đã lật
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        loop=gif.info.get("loop", 0),
        duration=gif.info.get("duration", 40),
        disposal=2,
        transparency=gif.info.get("transparency", 0),
    )

    print(f"✅ Đã lưu GIF lật thành công tại: {output_path}")

def rotate_gif(input_path, output_path, angle=90):
    """Xoay toàn bộ GIF theo góc cho trước (mặc định 90 độ)."""
    gif = Image.open(input_path)
    frames = []

    for frame in ImageSequence.Iterator(gif):
        # Chuyển frame sang RGBA
        frame = frame.convert("RGBA")
        # Xoay theo góc (expand=True để giữ đầy đủ ảnh)
        rotated = frame.rotate(angle, expand=True)
        frames.append(rotated)

    # Lưu lại GIF đã xoay
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        loop=gif.info.get("loop", 0),
        duration=gif.info.get("duration", 40),
        disposal=2,
        transparency=gif.info.get("transparency", 0),
    )
    print(f"✅ Đã xoay GIF {angle}° và lưu tại: {output_path}")

# === Ví dụ sử dụng ===
#flip_gif("gifs/slash_left.gif", "gifs/slash_right.gif", mode="horizontal")  # Lật ngang
#rotate_gif("gifs/slash_left.gif", "gifs/slash_down.gif", angle=90) 
#rotate_gif("gifs/slash_right.gif", "gifs/slash_down.gif", angle=-90)
flip_gif("gifs/slash_down.gif", "gifs/slash_up.gif", mode="vertical")
