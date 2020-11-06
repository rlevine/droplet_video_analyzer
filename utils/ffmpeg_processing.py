import ffmpeg
import time
import numpy as np
import os


def add_audio(in_file=None, out_file=None, combined_file=None, VERBOSE=False):
    """
    Combines audio data from source video file and annotated video
    into one file.

    :param in_file: str path to original video source file
    :param out_file: str path to annotated video output file.
    :param combined_file: str path file to new write
    :param VERBOSE: verbose flag

    TODO: an async progress meter would be nice.

    """
    if VERBOSE:
        print("\nProcessing audio...")

    analysis_start_time = time.time()

    QUIET = True
    # QUIET = False

    video_source_file = ffmpeg.input(out_file)
    audio_source_file = ffmpeg.input(in_file)
    video_component = video_source_file.video
    audio_component = audio_source_file.audio

    # Using a constant rate factor of 18 gives results almost indistinguishable
    # from the original opencv video. It also halves the file size.
    output = (
        ffmpeg.concat(video_component, audio_component, v=1, a=1)
        .output(
            combined_file,
            pix_fmt='yuv420p',
            crf=18,
            format='mov',
            shortest=1,
        )
        .overwrite_output()  # I'm confusing it, and it asks to overwrite otherwise??
    )

    command_line = ' '.join(
        ffmpeg.compile(output)
    )  # Just for debugging to see what it's sending.

    output.run(quiet=QUIET)

    analysis_end_time = time.time()

    if VERBOSE:
        print(
            "Processed audio in {:2.1f} seconds.\n".format(
                analysis_end_time - analysis_start_time
            )
        )

    if os.path.exists(combined_file):
        try:
            os.remove(out_file)
        except Exception as error:
            sys.exit(
                "\n\nOops. Cannot remove intermediate video file!\n{}\n{}\n".format(
                    output_dir, error
                )
            )


# Straight-through copy of video 0 and audio 1. How to do this with ffmpeg-python?
# ffmpeg -i in0.mp4 -i in1.mp4 -c copy -map 0:0 -map 1:1 -shortest out.mp4
# Would give up file size reduction, tho.


def get_normalized_audio_level_by_frame(in_file=None):

    QUIET = True
    # QUIET = False

    # Get file stream info.
    probe = ffmpeg.probe(in_file)
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    frame_rate = eval(video_info['avg_frame_rate'])  # Injection risk? Highly unlikely.
    num_frames = int(video_info['nb_frames'])

    audio_info = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    samples = int(audio_info['duration_ts'])
    sample_rate = int(audio_info['sample_rate'])
    channels = int(audio_info['channels'])
    codec = audio_info['codec_name']

    # Open file and separate out audio.
    audio_source_file = ffmpeg.input(in_file)
    audio_component = audio_source_file.audio

    # Write data to a stream, and suck it back into a numpy array.
    # 's16le' is raw data without header, in 16-bit signed ints.
    out, _ = audio_source_file.output('pipe:', format='s16le', ac=1).run(
        capture_stdout=True, quiet=QUIET
    )
    audio = np.frombuffer(out, np.int16)

    # Reshape to chunk and eliminate partial frames.
    samples_per_frame = int(sample_rate // frame_rate)
    audio = audio[: samples_per_frame * (audio.shape[0] // samples_per_frame)].reshape(
        -1, samples_per_frame
    )

    # Flip negative values and average.
    average_audio_by_frames = np.mean(abs(audio), axis=1)
    # Normalize, so we can scale it as needed.
    normalized_audio_by_frame = average_audio_by_frames / average_audio_by_frames.max(
        axis=0
    )
    # Pad with an extra zero, so we have as many data values as frames.
    # (Since we probably lost the less-than-frame tail of the data when we chunked it.)
    normalized_audio_by_frame = np.pad(
        normalized_audio_by_frame,
        (0, num_frames - len(normalized_audio_by_frame)),
        'constant',
    )

    return normalized_audio_by_frame
