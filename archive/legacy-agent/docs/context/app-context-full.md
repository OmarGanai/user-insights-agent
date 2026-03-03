# tenant App - UX and Features Documentation

## Overview

tenant is a family/home management platform that helps households organize their lives through task management, calendar integration, document storage, and AI assistance. The app follows a mobile-first design with a custom design system.

**Tech Stack:**
- **Frontend:** Next.js 15 (App Router), React 18, TypeScript, CSS Modules
- **State Management:** Zustand (modular stores)
- **Backend:** Express.js, Drizzle ORM, PostgreSQL
- **Mobile:** iOS native app with WebView integration

---

## App Architecture

```mermaid
graph TB
    subgraph "Frontend (Next.js)"
        WebApp[React Web App]
        iOS[iOS WebView]
    end
    
    subgraph "Backend Services"
        API[Node.js API]
        Calendar[Calendar Service]
        RAG[RAG Service]
        Push[Push Notifications]
    end
    
    subgraph "Storage"
        DB[(PostgreSQL)]
        Azure[Azure Blob]
        GCP[GCP Storage]
    end
    
    subgraph "External"
        OpenAI[OpenAI API]
        OAuth[OAuth Providers]
    end
    
    WebApp --> API
    iOS --> API
    API --> DB
    API --> Azure
    API --> GCP
    API --> Calendar
    API --> RAG
    RAG --> OpenAI
    API --> OAuth
    Push --> iOS
```

---

## Navigation Structure

The app uses a bottom tab bar with 4 main sections plus a floating action button for quick creation.

```mermaid
graph LR
    subgraph BottomTabBar["Bottom Tab Bar"]
        Home["Home"]
        Life["Life"]
        Time["Time"]
        People["People"]
    end
    
    FAB(("FAB"))
    
    FAB --> CreateTask["Create Task"]
    FAB --> CreateEvent["Create Event"]
    FAB --> CreateNote["Create Note"]
    FAB --> CreateDoc["Upload Document"]
```

### Main Tabs

| Tab | Route | Purpose |
|-----|-------|---------|
| **Home** | `/home` | Dashboard with Today/What's Next, Pinned items, Recent Activity |
| **Life** | `/life` | Hexagonal grid interface for spaces, appliances, utilities |
| **Time** | `/time` | Calendar view for events and tasks with deadlines |
| **People** | `/people` | Contact management and family members |

---

## Authentication Flow

```mermaid
flowchart TD
    Start([User Opens App]) --> AuthCheck{Authenticated?}
    
    AuthCheck -->|Yes| Home[Home Screen]
    AuthCheck -->|No| Login[Login Screen]
    
    Login --> EmailLogin[Email/Password]
    Login --> GoogleOAuth[Google OAuth]
    Login --> AppleOAuth[Apple OAuth]
    
    EmailLogin --> ValidateCreds{Valid?}
    ValidateCreds -->|Yes| StoreToken[Store JWT Token]
    ValidateCreds -->|No| ShowError[Show Error]
    ShowError --> Login
    
    GoogleOAuth --> OAuthCallback[OAuth Callback]
    AppleOAuth --> OAuthCallback
    OAuthCallback --> StoreToken
    
    StoreToken --> Home
    
    Login --> Register[Register]
    Register --> CreateAccount[Create Account]
    CreateAccount --> StoreToken
    
    Login --> ForgotPW[Forgot Password]
    ForgotPW --> SendCode[Send Reset Code]
    SendCode --> ValidateCode[Validate Code]
    ValidateCode --> ResetPW[Reset Password]
    ResetPW --> Login
```

### Auth Screens

| Screen | Route | Purpose |
|--------|-------|---------|
| Login | `/login` | Email/password + OAuth (Google/Apple) |
| Register | `/register` | New user signup |
| Forgot Password | `/forgot-password` | Request reset code |
| Validate Code | `/validate-code` | Enter verification code |
| Reset Password | `/reset-password` | Set new password |
| OAuth Callback | `/oauth-callback` | Handle OAuth redirects |

---

## Core Concepts: DENTS

DENTS is the unified term for the four core content types:

```mermaid
graph TB
    DENTS["DENTS"]
    DENTS --> D["Documents"]
    DENTS --> E["Events"]
    DENTS --> N["Notes"]
    DENTS --> T["Tasks"]
    
    D --> DFeatures["Upload - Storage - Categories"]
    E --> EFeatures["Scheduling - Recurring - Calendar Sync"]
    N --> NFeatures["Checklists - Deadlines - Attachments"]
    T --> TFeatures["Priorities - Assignment - Deadlines"]
```

### DENT Entity Relationships

```mermaid
erDiagram
    TASK ||--o{ FILE : has
    TASK ||--o{ CONTACT : involves
    TASK ||--o| TILE : associated_with
    TASK ||--o| USER : assigned_to
    
    EVENT ||--o{ FILE : has
    EVENT ||--o{ CONTACT : involves
    EVENT ||--o| CALENDAR : belongs_to
    EVENT ||--o{ EVENT_TIME : has_instances
    
    NOTE ||--o{ FILE : has
    NOTE ||--o| TILE : associated_with
    NOTE ||--o| TASK : linked_to
    NOTE ||--o| EVENT : linked_to
    
    FILE ||--o| TILE : attached_to
    FILE ||--o| CONTACT : associated_with
    
    USER ||--|{ ACCOUNT : belongs_to
    CONTACT ||--o| ACCOUNT : belongs_to
    TILE ||--o| ACCOUNT : belongs_to
```

---

## Hive System (Household Management)

The Hive system organizes family members into households for shared management.

```mermaid
graph TB
    subgraph Account["Account - Household"]
        Owner["Owner Admin"]
        Member1["Family Member 1"]
        Member2["Family Member 2"]
        Member3["Child"]
    end
    
    subgraph Tiles["Shared Tiles"]
        Space1["Living Room"]
        Space2["Kitchen"]
        Appliance1["Refrigerator"]
        Utility1["Electricity"]
    end
    
    subgraph SharedContent["Shared DENTS"]
        Task1["Buy groceries"]
        Event1["Family dinner"]
        Note1["Shopping list"]
    end
    
    Owner --> Space1
    Member1 --> Space1
    Member2 --> Space2
    
    Task1 --> Member1
    Event1 --> Owner
```

### Tile Types

```mermaid
graph LR
    Tile["Hexagonal Tile"]
    
    Tile --> Space["Space"]
    Tile --> Appliance["Appliance"]
    Tile --> Utility["Utility"]
    Tile --> Property["Property"]
    
    Space -->|Examples| SpaceEx["Living Room - Kitchen - Garage"]
    Appliance -->|Examples| AppEx["Refrigerator - HVAC - Washer"]
    Utility -->|Examples| UtilEx["Electricity - Water - Gas - Internet"]
    Property -->|Examples| PropEx["Address - Insurance - HOA"]
```

---

## Screen Flow Diagrams

### Home Tab Flow

```mermaid
flowchart TD
    Home["Home Screen"] --> Today["Today - Whats Next Section"]
    Home --> Pinned["Pinned Items Carousel"]
    Home --> Activity["Recent Activity Feed"]
    
    Today --> ViewTask["View Task"]
    Today --> ViewEvent["View Event"]
    
    Pinned --> ViewAny["View Pinned Item"]
    
    Activity --> ViewActivity["View Activity Detail"]
    
    ViewTask --> EditTask["Edit Task"]
    ViewEvent --> EditEvent["Edit Event"]
    
    Home --> Search["Search"]
    Home --> Profile["Profile"]
    Home --> Settings["Settings"]
```

### Life Tab Flow (Hex Grid)

```mermaid
flowchart TD
    Life["Life Screen"] --> HexGrid["Hexagonal Grid"]
    
    HexGrid --> SpaceTile["Space Tile"]
    HexGrid --> ApplianceTile["Appliance Tile"]
    HexGrid --> UtilityTile["Utility Tile"]
    
    SpaceTile --> SpaceDetail["Space Detail"]
    SpaceDetail --> SpaceEdit["Edit Space"]
    SpaceDetail --> SpaceDENTS["View Space DENTS"]
    
    ApplianceTile --> ApplianceDetail["Appliance Detail"]
    ApplianceDetail --> ApplianceEdit["Edit Appliance"]
    ApplianceDetail --> ScanLabel["Scan Label"]
    
    UtilityTile --> UtilityDetail["Utility Detail"]
    UtilityDetail --> UtilityEdit["Edit Utility"]
    
    Life --> AllDENTS["View All DENTS"]
    Life --> MyHive["My Hive"]
    
    MyHive --> MemberDetail["Member Detail"]
    MemberDetail --> EditMember["Edit Member"]
```

### Time Tab Flow (Calendar)

```mermaid
flowchart TD
    Time[Time Screen] --> CalendarView[Calendar View]
    
    CalendarView --> DayView[Day View]
    CalendarView --> WeekView[Week View]
    CalendarView --> MonthView[Month View]
    
    DayView --> EventDetail[Event Detail]
    DayView --> TaskWithDeadline[Task with Deadline]
    
    EventDetail --> EditEvent[Edit Event]
    EventDetail --> MarkComplete[Mark Complete]
    
    Time --> CreateEvent[+ Create Event]
    Time --> ManageCalendars[Manage Calendars]
```

### People Tab Flow

```mermaid
flowchart TD
    People["People Screen"] --> ContactList["Contact List"]
    
    ContactList -->|Filter| FilterByType{"Filter by Type"}
    FilterByType --> Family["Family"]
    FilterByType --> Medical["Medical"]
    FilterByType --> Education["Education"]
    FilterByType --> Provider["Provider"]
    FilterByType --> Community["Community"]
    FilterByType --> Lifestyle["Lifestyle"]
    
    ContactList --> ContactDetail["Contact Detail"]
    ContactDetail --> EditContact["Edit Contact"]
    ContactDetail --> ContactDENTS["Contact DENTS"]
    
    People --> AddContact["Add Contact"]
    People --> ImportContacts["Import from Device"]
```

### Create/Edit DENT Flow

```mermaid
flowchart TD
    FAB(("+ Button")) --> CreateMenu["Create Menu"]
    
    CreateMenu --> CreateTask["Create Task"]
    CreateMenu --> CreateEvent["Create Event"]
    CreateMenu --> CreateNote["Create Note"]
    CreateMenu --> UploadDoc["Upload Document"]
    
    CreateTask --> TaskForm["Task Form"]
    TaskForm --> SetTitle["Set Title and Description"]
    SetTitle --> SetPriority["Set Priority"]
    SetPriority --> SetDeadline["Set Deadline"]
    SetDeadline --> AssignTo["Assign To"]
    AssignTo --> LinkTile["Link to Tile"]
    LinkTile --> AddPeople["Add People Involved"]
    AddPeople --> SaveTask["Save Task"]
    
    CreateEvent --> EventForm["Event Form"]
    EventForm --> EventTitle["Set Title and Details"]
    EventTitle --> SetSchedule["Set Date and Time"]
    SetSchedule --> SetRecurrence["Set Recurrence"]
    SetRecurrence --> SelectCalendar["Select Calendar"]
    SelectCalendar --> AddAttendees["Add Attendees"]
    AddAttendees --> SaveEvent["Save Event"]
```

---

## Design System

### Color Palette

```mermaid
graph LR
    subgraph Primary
        ElectricBlue["#2A46BE<br/>Electric Blue"]
        Blue["#000E50<br/>Blue"]
        Midnight["#000728<br/>Midnight"]
    end
    
    subgraph Secondary
        Purple["#C3B7FF<br/>Purple"]
        Lavender["#95A3DF<br/>Lavender"]
        Aqua["#6FF9D8<br/>Aqua"]
    end
    
    subgraph Status
        Red["#D70015<br/>Red/High"]
        Green["#6CC47C<br/>Green/Low"]
        Mustard["#FFA020<br/>Mustard/Medium"]
    end
```

### Priority Color Coding

| Priority | Color | Hex |
|----------|-------|-----|
| None | Grey | `#BABACA` |
| Low | Green | `#6CC47C` |
| Medium | Mustard | `#FFA020` |
| High | Red | `#D70015` |

### Typography

- **Primary Font:** Poppins (Regular, Medium, Semibold, Bold)
- **Secondary Font:** ABeeZee (Regular, Italic)
- **Size Range:** 8px - 50px

---

## UI Components

### Component Library

```mermaid
graph TB
    subgraph "Core Components"
        Button[Button]
        Input[Input]
        Modal[Modal]
        Card[Card]
    end
    
    subgraph "Layout Components"
        TabBar[TabBar]
        PageHeader[PageHeader]
        ContentWrapper[ContentWrapper]
    end
    
    subgraph "Feature Components"
        DENTCard[DENTCard]
        HexGrid[HexGrid]
        Calendar[Calendar]
        assistantChat[BassistantChat]
    end
    
    subgraph "Feedback Components"
        Snackbar[Snackbar]
        Toast[Toast]
        LoadingSpinner[LoadingSpinner]
        SkeletonLoader[SkeletonLoader]
    end
```

### Modal Types

| Modal | Purpose |
|-------|---------|
| `UserSelectionModal` | Select family members |
| `HiveSelectionModal` | Select household |
| `ApplianceSelectionModal` | Select appliances |
| `DocumentUploadModal` | Upload files |
| `TextInputsModal` | Multi-field text input |
| `DateTimeSelectionView` | Date/time picker |
| `PrioritySelectionView` | Priority selector |

### Notification System

```mermaid
sequenceDiagram
    participant Action
    participant Snackbar
    participant Toast
    participant User
    
    Action->>Snackbar: emitSnackbar(type, message)
    Snackbar->>User: Show top-center notification
    Note over Snackbar: Auto-dismiss after 3s
    
    Action->>Toast: showToast(type, message)
    Toast->>User: Show top-right notification
    Note over Toast: Slide-in animation
```

---

## AI Features (tenant)

```mermaid
flowchart LR
    User[User] --> Chat[tenant Chat]
    Chat --> Query[User Query]
    Query --> RAG[RAG Service]
    RAG --> Context[Fetch Context]
    Context --> OpenAI[OpenAI API]
    OpenAI --> Stream[Streaming Response]
    Stream --> Chat
    Chat --> User
    
    subgraph "Context Sources"
        Context --> Tasks[Tasks]
        Context --> Events[Events]
        Context --> Notes[Notes]
        Context --> Tiles[Tiles]
    end
```

**tenant AI chat Features:**
- Natural language queries about home management
- Context-aware responses using household data
- Streaming responses for real-time feedback
- Accessible via chat interface at `/assistant-chat`

---

## Data Flow

### State Management (Zustand)

```mermaid
graph TB
    subgraph "Zustand Stores"
        TilesStore[tiles store]
        TimelineStore[timeline store]
        PinnedStore[pinned store]
        TileDentsStore[tileDents store]
    end
    
    subgraph "API Layer"
        Services[Service Layer]
        API[Backend API]
    end
    
    subgraph "Components"
        HomeScreen[Home Screen]
        LifeScreen[Life Screen]
        TimeScreen[Time Screen]
    end
    
    HomeScreen --> TimelineStore
    HomeScreen --> PinnedStore
    LifeScreen --> TilesStore
    LifeScreen --> TileDentsStore
    TimeScreen --> Services
    
    TilesStore --> Services
    TimelineStore --> Services
    Services --> API
```

### API Response Flow

```mermaid
sequenceDiagram
    participant Component
    participant Store
    participant Service
    participant API
    participant DB
    
    Component->>Store: dispatch action
    Store->>Service: call service method
    Service->>API: HTTP request
    API->>DB: query
    DB-->>API: data
    API-->>Service: response (camelCase)
    Service-->>Store: mapped data (PascalCase)
    Store-->>Component: updated state
    Component->>Component: re-render
```

---

## Key User Flows

### Adding a New Task

```mermaid
sequenceDiagram
    actor User
    participant FAB as FAB Button
    participant Form as Task Form
    participant API as API Server
    participant Store as State Store
    
    User->>FAB: Tap FAB
    FAB->>Form: Open Create Task
    User->>Form: Enter title
    User->>Form: Set priority
    User->>Form: Set deadline
    User->>Form: Assign to family member
    User->>Form: Link to tile
    User->>Form: Tap Save
    Form->>API: POST task data
    API-->>Store: Update timeline
    Store-->>User: Show in Home feed
```

### Managing Appliances

```mermaid
sequenceDiagram
    actor User
    participant Life as Life Tab
    participant Tile as Appliance Tile
    participant Scanner as Label Scanner
    participant AI as OpenAI API
    
    User->>Life: Navigate to Life tab
    User->>Tile: Tap appliance hex
    Tile->>User: Show appliance detail
    User->>Scanner: Tap Scan Label
    Scanner->>User: Open camera
    User->>Scanner: Capture label photo
    Scanner->>AI: Extract info from image
    AI-->>Scanner: Return appliance details
    Scanner-->>Tile: Auto-fill fields
    User->>Tile: Save appliance
```

---

## Screen Inventory

### Main Screens

| Category | Screen | Route |
|----------|--------|-------|
| **Auth** | Login | `/login` |
| | Register | `/register` |
| | Forgot Password | `/forgot-password` |
| **Tabs** | Home | `/home` |
| | Life | `/life` |
| | Time | `/time` |
| | People | `/people` |
| **Tasks** | Create Task | `/create-task` |
| | Edit Task | `/edit-task/[id]` |
| | View Task | `/view-task/[id]` |
| **Events** | Create Event | `/create-event` |
| | Edit Event | `/edit-event/[id]` |
| | View Event | `/view-event/[id]` |
| **Notes** | Create Note | `/create-note` |
| | Edit Note | `/edit-note/[id]` |
| | View Note | `/view-note/[id]` |
| **Documents** | Create Document | `/create-doc` |
| | Edit Document | `/edit-document` |
| | View Document | `/document-viewer` |
| **Tiles** | Tile Detail | `/tile/[id]` |
| | Spaces | `/spaces` |
| | Space Detail | `/space-detail/[id]` |
| | Appliances | `/appliances` |
| | Appliance Detail | `/appliance-detail/[id]` |
| | Utilities | `/utilities` |
| | Utility Detail | `/utility-detail/[type]` |
| **People** | Contact Detail | `/people/[id]` |
| | New Contact | `/people/new` |
| | Edit Contact | `/people/[id]/edit` |
| **Hive** | My Hive | `/my-hive` |
| | Member Detail | `/my-hive/member/[id]` |
| | Hive Selection | `/hive-selection` |
| **Settings** | Settings | `/settings` |
| | Profile | `/profile` |
| | Edit Profile | `/profile/edit` |
| **Other** | Search | `/search` |
| | tenant Chat | `/assistant-chat` |
| | Calendars | `/calendars` |

---

## Mobile App Integration

The web app supports WebView integration with the native iOS app:

```mermaid
graph TB
    subgraph iOS["iOS Native App"]
        NativeNav[Native Navigation]
        NativeTabBar[Native Tab Bar]
        WebView[WKWebView]
    end
    
    subgraph Web["Next.js Web App"]
        Pages[Page Components]
        TabBarComp[TabBar Component]
        AuthGuard[Auth Guard]
    end
    
    NativeNav --> WebView
    WebView --> Pages
    
    Pages --> |mobile=true| HideWebTabBar[Hide Web Tab Bar]
    Pages --> |token=jwt| AuthGuard
    
    NativeTabBar --> WebView
```

**Mobile-specific behaviors:**
- Tab bar hidden when `?mobile=true` (uses native iOS tab bar)
- JWT token passed via `?token=` parameter
- Navigation preserves mobile parameters across routes

---

## Recurring Patterns

The app supports recurring tasks and events using RRule:

```mermaid
graph LR
    Recurrence[Recurrence Pattern]
    
    Recurrence --> Daily[Daily]
    Recurrence --> Weekly[Weekly]
    Recurrence --> Monthly[Monthly]
    Recurrence --> Yearly[Yearly]
    Recurrence --> Custom[Custom RRule]
    
    Event --> |has| EventTimes[Event Times]
    EventTimes --> |instances| Instance1[Instance 1]
    EventTimes --> Instance2[Instance 2]
    EventTimes --> InstanceN[Instance N...]
```

---

## Summary

Tenant is a comprehensive family management app with:

- **4 main tabs:** Home, Life, Time, People
- **Core content types (DENTS):** Documents, Events, Notes, Tasks
- **Hive system:** Multi-user household management
- **Tile-based organization:** Hexagonal grid for spaces, appliances, utilities
- **AI assistant (tenant):** Context-aware home management help
- **Cross-platform:** Web + iOS native app integration
- **Custom design system:** Consistent UI with Poppins font, blue/purple color palette
