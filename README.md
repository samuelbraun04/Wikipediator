# Wikipediator

### STATUS:

*Wikipediator is in still in development. Currently, the script cannot generate a video – but it can get all the required ingredients. The video-making process will be made sometime in the near future.*

### DESCRIPTION:

Wikipediator gets yesterday's most popular Wikipedia pages and turns them into videos. These videos are then uploaded to YouTube via the YouTube Upload API. The generated video consists of two streams of content – audio and video:

- The audio content of the generated video is a Amazon Polly TTS read of the chosen Wikipedia page's summary.
- The video content of the generated video is a slideshow of images (along with captions for context) from the chosen Wikipedia page.