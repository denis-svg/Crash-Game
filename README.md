# Crash-Game
## Usage

Run:
```CMD
docker compose up --build
```

## Application Suitability

In a crash gamble game, different parts of the system can experience varying levels of traffic depending on events like peak gaming hours, promotions, or special tournaments. By using a microservices architecture, individual high-traffic components, such as the matchmaking service or lobby management, can be scaled independently, ensuring optimal performance without impacting other parts of the system.

Microservices also facilitate independent development, allowing teams to work on distinct features without causing disruptions. For example, the crash game’s lobby system can be maintained by a dedicated team that can deploy updates, introduce new game modes, or address bugs without affecting other critical services, such as the payment gateway or real-time gameplay engine. This allows for faster iterations and continuous improvement, ensuring a smooth user experience.

Netflix Video Processing Pipeline with Microservices (https://netflixtechblog.com/rebuilding-netflix-video-processing-pipeline-with-microservices-4e5e6310e359)
Starting in 2014, netflix developed and operated the video processing pipeline on their third-generation platform Reloaded. 
Reloaded was initially designed as a monolithic system for converting high-quality media files into streaming assets for Netflix. Over time, its complexity grew as new functionalities were added, leading to tightly coupled modules, long release cycles, and development inefficiencies. This structure made it difficult to introduce new features, slowed down development, and ultimately hindered innovation.

In 2018, Netflix developed Cosmos, a media-centric microservices platform designed to improve flexibility and feature development velocity over the monolithic Reloaded system. Cosmos employs microservices, each focused on a specific function in the media pipeline, such as Video Encoding Service (VES) and Video Quality Service (VQS), to decouple complex processes like encoding and quality assessment. Each service operates independently, and service orchestration is customized for two main use cases: member streaming, which focuses on high-quality, scalable video assets, and studio operations, which prioritize fast turnaround for production needs. This architecture enhances scalability, experimentation, and innovation.

## Service boundaries
![32131 drawio](https://github.com/user-attachments/assets/ae85c94c-6562-4ad0-8331-7203b46855c3)

## Data Management

The interface of the api and websockets can be tested in open-api interface. Below there is a list of endpoints from both services

- Service A

POST /gateway/user/v1/auth/register
```json
{
  "username": "user123",
  "password": "johnDoe",
}
```

POST /gateway/user/v1/auth/login
```json
{
  "username": "user123",
  "password": "johnDoe",
}
```

POST /gateway/user/v1/auth/validate
expects: jwt token

GET /gateway/user/v1/balance
expects: jwt token

PUT /gateway/user/v1/balance
```json
{
  "ammount": 1000
}
```
expects: jwt token

POST /gateway/user/v1/balance
expects: jwt token
```json
{
  "ammount": 1000
}
```

- Service B

POST /gateway/game/v1/lobby
expects: jwt token

GET /gateway/game/v1/lobby/<int:lobby_id>

# Web sockets
connect
```
{'message': 'WebSocket connection established'}
```

joinRoom
```
{'lobby_id': '4'}
```

```
'Joined room: {4}'
```

place_bet
```
{token:"jwt_token"]
```

withdraw
```
{token:"jwt_token"]
```

## Deployment & Scaling
All services, including Gateway, Service discovery, databases and Prometheus + Grafana run inside Docker containers and are managed with Docker Compose.

