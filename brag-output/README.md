# The 25-second Brag demo

[Watch the video](brag.mp4) · [Read the transcript](../docs/DEMO_TRANSCRIPT.md)

This video explains the saved money-converter experiment with an AI-generated voice and quiet music. It is an animated explanation, not a live screen recording.

Only three files are needed here:

- `brag.mp4`: the finished video, including its audio.
- `brag.jpg`: the cover image shown in the project README.
- `README.md`: this explanation and the music credits.

Made with [Brag](https://github.com/latent-spaces/brag), Hyperframes 0.9.46, and a locally generated Kokoro voice. The video is 25 seconds, full HD, and 30 frames per second. No OpenAI requests were needed to make it.

The editing source, raw audio, plans, and temporary files have been removed. Playback is unaffected; future changes to the animation will require rebuilding the source.

## Credits and licenses

**Music: Sascha Ende, ende.app (CC BY 4.0).** “Happy Beats Business Moves Vol. 12,” supplied with Brag. [Music source](https://ende.app/en) · [License](https://ende.app/en/standard-license). The video uses the opening 25 seconds at reduced volume with fades. Music retains its own license, separate from the project's code license.

**Sound effect:** Kenney, CC0, `bong_001.ogg`, supplied with Brag. [Kenney](https://kenney.nl/).

**Voice:** synthetic Kokoro-82M voice, `af_heart`; generated locally. **Animation:** Hyperframes with GSAP; hook reveal adapted from Hyperframes' `blur-in` registry component.
