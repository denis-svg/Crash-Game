# Crash-Game

## Application Suitability

In a crash gamble game, different parts of the system can experience varying levels of traffic depending on events like peak gaming hours, promotions, or special tournaments. By using a microservices architecture, individual high-traffic components, such as the matchmaking service or lobby management, can be scaled independently, ensuring optimal performance without impacting other parts of the system.

Microservices also facilitate independent development, allowing teams to work on distinct features without causing disruptions. For example, the crash game’s lobby system can be maintained by a dedicated team that can deploy updates, introduce new game modes, or address bugs without affecting other critical services, such as the payment gateway or real-time gameplay engine. This allows for faster iterations and continuous improvement, ensuring a smooth user experience.

Netflix Video Processing Pipeline with Microservices (https://netflixtechblog.com/rebuilding-netflix-video-processing-pipeline-with-microservices-4e5e6310e359)
Starting in 2014, netflix developed and operated the video processing pipeline on their third-generation platform Reloaded. 
Reloaded was initially designed as a monolithic system for converting high-quality media files into streaming assets for Netflix. Over time, its complexity grew as new functionalities were added, leading to tightly coupled modules, long release cycles, and development inefficiencies. This structure made it difficult to introduce new features, slowed down development, and ultimately hindered innovation.

In 2018, Netflix developed Cosmos, a media-centric microservices platform designed to improve flexibility and feature development velocity over the monolithic Reloaded system. Cosmos employs microservices, each focused on a specific function in the media pipeline, such as Video Encoding Service (VES) and Video Quality Service (VQS), to decouple complex processes like encoding and quality assessment. Each service operates independently, and service orchestration is customized for two main use cases: member streaming, which focuses on high-quality, scalable video assets, and studio operations, which prioritize fast turnaround for production needs. This architecture enhances scalability, experimentation, and innovation.

## Service Boundaries
![444444444444](https://github.com/user-attachments/assets/69c58771-9e20-46ae-b5a2-3ccae60f76a1)

## Data Management

- Service A

POST /user/auth/register
```json
{
  "userId": "user123",
  "username": "johnDoe",
  "email": "johndoe@example.com",
  "status": "registered"
}
```

POST /user/auth/login
```json
{
  "userId": "user123",
  "token": "eyJhbGciOiJIUzI1NiIsInR...",
  "status": "authenticated"
}
```

POST /user/auth/validate

GET /user/{userId}/balance
```json
{
  "userId": "user123",
  "balance": 1000
}
```

POST /user/{userId}/balance
```json
{
  "userId": "user123",
  "newBalance": 900
}
```

GET /user/{userId}/profile
```json
{
  "userId": "user123",
  "username": "johnDoe",
  "email": "johndoe@example.com"
}
```

- Service B

POST /game/lobby/create
```json
{
  "lobbyId": "lobby123",
  "lobbyName": "HighStakes",
  "maxPlayers": 10,
  "status": "created"
}
```

GET /game/lobbies
```json
[
  {
    "lobbyId": "lobby123",
    "lobbyName": "HighStakes",
    "currentPlayers": 5,
    "maxPlayers": 10
  },
  {
    "lobbyId": "lobby456",
    "lobbyName": "LowStakes",
    "currentPlayers": 2,
    "maxPlayers": 5
  }
]
```
### Websockets
/web_socket/<lobby_id>/
Join a Lobby

```json
{
  "action": "join",
  "userId": "user123",
  "lobbyId": "lobby123",
  "status": "joined"
}
```

Place a Bet

```json
{
  "action": "bet",
  "userId": "user123",
  "lobbyId": "lobby123",
  "gameId": "game789",
  "betAmount": 100,
  "status": "bet placed"
}
```

Receive Game Status Updates

```json
{
  "action": "statusUpdate",
  "lobbyId": "lobby123",
  "gameId": "game789",
  "currentMultiplier": 2.5,
  "status": "in-progress"
}
```

Cash Out

```json
{
  "action": "cashout",
  "userId": "user123",
  "gameId": "game789",
  "multiplier": 3.2,
  "payout": 320,
  "status": "cashed out"
}
```


## Deployment & Scaling
 * Docker to containerize each microservice in order to ensure that each service can run independently in a Docker container.
 * Kubernetes for managing the deployment, scaling, and load balancing. This will allow you to automatically scale the microservices based on demand.

