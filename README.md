# fxd-tiktok-bot

## Docker Setup

### Building the Docker Image

To build the Docker image, run:

```bash
docker build -t fxd-tiktok-bot .
```

### Running the Container

Run the container with your Telegram bot token and admin ID:

```bash
docker run -d --name tiktok-bot \
  -e BOT_TOKEN=your_telegram_bot_token \
  -e ADMIN_ID=your_telegram_user_id \
  fxd-tiktok-bot
```

Replace `your_telegram_bot_token` with your actual Telegram bot token and `your_telegram_user_id` with your Telegram user ID.

### Checking Logs

To check the logs of the running container:

```bash
docker logs -f tiktok-bot
```

### Stopping the Container

To stop the container:

```bash
docker stop tiktok-bot
```

## Environment Variables

The bot requires the following environment variables:

- `BOT_TOKEN`: Your Telegram bot token (get it from @BotFather)
- `ADMIN_ID`: Your Telegram user ID (the bot will send downloaded videos to this ID)

## Features

- todo