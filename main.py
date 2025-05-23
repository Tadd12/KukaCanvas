import sys

from website.kuka import converter
from website.image_stuff import image_conversion



if __name__ == "__main__":
    # Example usage: python main.py <image_path> <output_path> <blur_intensity> <threshold_block_size> <threshold_C>

    # Get parameters from command
    print("Command line arguments:", sys.argv)
    sys.argv.pop(0)  # Remove the script name from the arguments

    if len(sys.argv) < 1:
        print("Usage: python main.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[0]
    print("Image path:", image_path)

    if len(sys.argv) < 3:
        try:
            contours = image_conversion.process_image(image_path, 5, 11, 2)
        except Exception as e:
            print(f"Error processing image: {e}")
            sys.exit(1)

    else:
        params = [5, 11, 2]
        # Change the parameters based on command line arguments if provided whilst keeping in mind
        # that the first two arguments are the image path and the script name

        for i in range(2, len(sys.argv)):
            try:
                params[i - 2] = int(sys.argv[i])
            except ValueError:
                print(f"Invalid parameter: {sys.argv[i]}. Using default value.")

        print("Using parameters:", params)
        try:
            contours = image_conversion.process_image(image_path, *params)
        except Exception as e:
            print(f"Error processing image: {e}")
            sys.exit(1)

    # print("Contours:", contours)

    # KRL script generation
    output_path = sys.argv[1] if len(sys.argv) > 1 else "draw.src"
    print("Output path:", output_path)
    try:
        krl_script = converter.generate_krl_script(contours, filename=output_path, save=True)
        krl_script_string = "\n".join(krl_script)
        print("KRL Script:\n", krl_script_string)
    except Exception as e:
        print(f"Error generating KRL script: {e}")
        sys.exit(1)
