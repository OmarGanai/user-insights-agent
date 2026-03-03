# PRD: Product Analytics for Dragon's Den Launch

**Author:** Omar Ganai   
**Date:** 2025-09-22   
**Status:** In production

## 1\. Why Are We Doing This?

The goal here is to **learn**, not just to see vanity metrics. The traffic from Dragon's Den is the most valuable user research we will ever get, and we must be ready to learn from it.

This is about discovering what makes tenant click for users so we can double down on what works. 

## 2\. What Does Success Look Like?

Success isn't just shipping this. Success is using the data to **make confident choices about what tenant should become.** 

The tracking plan below is designed to help us prove or disprove our main ideas for the product's future.

### Future Product Bets (DRAFT)

We're using this launch to stress-test three big ideas. We want to understand who our users are and what "job" they are hiring tenant for.

* **Bet 1: Is tenant a "Family Operating System"?** We'll look for lots of sharing between family members and content about family life (e.g., school forms, appointments).  
* **Bet 2: Is tenant a "Personal Chief of Staff"?** We'll look for "power user" behavior in tasks and content related to personal productivity.  
* **Bet 3: Is tenant an "Intelligent Document Hub"?** We'll look for users uploading lots of different file types and using the app like a personal search engine.

Success means we can confidently say which of these groups is our strongest user base.

## 3\. North Star Metric & The "Aha Moment"

[Based on previous user research from marketing](https://tenant.atlassian.net/wiki/spaces/SD/pages/75661363/User+insights+from+case+study+interviews+Draft), the main problem tenant solves is reducing the "mental load" of running a household. When this mental load becomes too much, it leads to coordination breakdown, creating the motivation for users to seek out a “solution” like tenant.

### North Star Metric: Total Shared Items

For now, our North Star Metric will be **Total Shared Items**. 

This is a count of all DENTs (Documents, Events, Notes, and Tasks) that are created and then shared with someone else in a user's "Hive." This number shows us that real collaboration is happening.

Guardrails (track alongside to ensure it reflects value, not spam):

- % Shared items viewed by 1+ HIVE member within 3 days  
- % Shared items that trigger at least one action from assigned member  
- Duplicate/low-signal rate (e.g. empty or single word DENTs)  
- Time to first shared items (first item, 3 items, 10 items)

### The "Aha Moment"

We believe the "aha moment" is:

When a user creates and shares a DENT for the first time and feels the relief of getting an idea or a task out of their own head and into a shared, trusted space.

## 4\. Key User Journeys to Track

To see if users are getting to that "aha moment," we'll track two main journeys.

### 4.1. Sign-up Funnel (P0)

This helps us see how well our sign-up process is working.

1. **`Signup: Begun`**: User lands on the sign-up/login screen.  
2. **`Signup: Method Selected`**: User chooses a sign-up method (email, Google, Apple).  
3. **`Signup: Completed`**: User successfully creates a new account.

### 4.2. First-Time Activation Journey (P0)

This is the most important journey. It tracks a new user from a blank slate to feeling the magic of the app.

1. **`FTUE: Begun`**: User signs up and sees the Home screen for the first time.  
2. **`FTUE: First Item Created`**: User creates their first item (Task, Note, etc.).  
3. **`FTUE: First Hive Invite`**: User invites someone to their Hive.  
4. **`FTUE: Completed (First Item Assigned)`**: User assigns an item to someone else. A user who does this is considered **"activated."**

## 5\. User Properties (Traits)

For every event, we need to be able to slice the data by who the user is.

* `email`: User's email.  
* `user_id`: User's unique ID.  
* `plan_type`: Their subscription plan (e.g., free, premium).  
* `hive_role`: Their role in their Hive (e.g., admin, member).  
* `hive_id`: The ID for their Hive.  
* `hive_member_count`: How many people are in their Hive.  
* `creation_date`: When they signed up.  
* `property_situation`: If they Own or Rent.

## 6\. Event Taxonomy

**A Note to Engineering:** The property names and example values in the tables below are illustrative. They are designed to communicate the \*business goal\* and the \*user value\* we need to measure. I’m relying on you to propose the best technical implementation. Please feel free to suggest changes to property names for technical clarity or consistency, as long as the core business requirement is met.

Here's the full list of events, prioritized by P0 (Must-Have for Launch), P1 (Important), and P2 (Nice-to-Have; can be post launch).

### 6.1. User Account Events

| Priority | Event Name | Trigger | Properties |
| :---- | :---- | :---- | :---- |
| **P0** | `Signup: Begun` | User lands on the sign-up/login screen. | `entry_point` |
| **P0** | `Signup: Method Selected` | User chooses a sign-up method. | `signup_method` (email, google, apple) |
| **P0** | `Signup: Completed` | User successfully creates a new account. | `signup_method` |
| **P1** | `Signup: Failed` | User fails to create an account. | `signup_method`, `error_message` |
| **P2** | `User: Logged In` | User successfully logs in. | `login_method` |
| **P2** | `User: Logged Out` | User successfully logs out. |  |
| **P2** | `User: Password Reset Requested` | User requests a password reset link. |  |
| **P2** | `User: Password Reset Completed` | User successfully resets their password. |  |
| **P2** | `User: Account Deleted` | User deletes their account. |  |

### 6.2. Creating and Sharing DENTs 

This is how we'll measure our "Total Shared Items" North Star Metric. 

The loop is: 

1. someone creates and shares an item, and   
2. someone else views or acts on it.

The creator\_user\_id field allows us to track the success of our sharing collaboration loop from start to finish. It's the key to measuring our North Star Metric, "Total Shared Items."

1. You create a task and assign it to me. The Task: Created event fires.  
2. When I open the app and view that task, the Task: Viewed event fires. The main user\_id for this event is mine, because I'm the one performing the action.  
3. The creator\_user\_id property on that Task: Viewed event will contain your user ID.Without creator\_user\_id, all we know is that I viewed a task. We have no idea if it was a task you created or a task someone else created. The loop is broken.

With creator\_user\_id, we can connect my action back to your creation. We can definitively say, "The task Omar created was successfully viewed by his Hive member."

#### Tasks

| Priority | Event Name | Trigger | Properties | What it tells us |
| :---- | :---- | :---- | :---- | :---- |
| **P0** | `Task: Created` | User creates a new task. | `is_recurring` | Starts the sharing loop. |
| **P0** | `Task: Assigned` | User assigns a task. | `assignee_type`, `creator_user_id` | The act of sharing. |
| **P0** | `Task: Viewed` | User views the details of a task. | `creator_user_id` | The other person saw it. |
| **P0** | `Task: Completed` | User marks a task as complete. | `is_recurring`, `creator_user_id` | The other person completes the task. Loop was successful. |
| **P2** | `Task: Edited` | User edits an existing task. | `creator_user_id` | A mid-loop interaction. |
| **P2** | `Task: Deleted` | User deletes a task. | `creator_user_id` | Breaks the loop. |

#### 

#### Notes, Events, & Documents

| Priority | Event Name | Trigger | Properties | Role in Collaboration Loop |
| :---- | :---- | :---- | :---- | :---- |
| **P0** | `Note: Created` | User creates a new note. |  | Starts the loop. |
| **P0** | `Note: Viewed` | User views a note. | `creator_user_id` | Confirms the shared item was received. |
| **P2** | `Note: Edited` | User edits a note. | `creator_user_id` | A mid-loop interaction. |
| **P2** | `Note: Deleted` | User deletes a note. | `creator_user_id` | Breaks the loop. |
| **P0** | `Event: Created` | User creates a new calendar event. |  | Starts the loop. |
| **P0** | `Event: Viewed` | User views an event. | `creator_user_id` | Confirms the shared item was received. |
| **P2** | `Event: Edited` | User edits an event. | `creator_user_id` | A mid-loop interaction. |
| **P2** | `Event: Deleted` | User deletes an event. | `creator_user_id` | Breaks the loop. |
| **P0** | `Document: Uploaded` | User uploads a document. | `file_type` | Starts the loop. |
| **P0** | `Document: Viewed` | User views a document. | `creator_user_id` | Confirms the shared item was received. |
| **P2** | `Document: Deleted` | User deletes a document. | `creator_user_id` | Breaks the loop. |

### 6.3. Hive & House Management

These events relate to the setup and management of the household.

| Priority | Event Name | Trigger | Properties |
| :---- | :---- | :---- | :---- |
| **P0** | `Hive: Member Invited` | User invites someone to join their Hive. |  |
| **P0** | `Hive: Member Joined` | An invited user accepts and joins a Hive. |  |
| **P2** | `Hive: Member Role Changed` | User changes a member's role (e.g., active/passive). | `new_role` |
| **P1** | `House: Tile Tapped` | User taps on a location tile (e.g., "Kitchen"). | `tile_name` |
| **P1** | `House: Appliance Added` | User adds a new appliance to their house. | `appliance_type` |
| **1** | `House: Space Added` | User adds a new space to their house. | `space_type` |
| **P1** | `House: Utility Added` | User adds a new utility provider. | `utility_type` |
| **P1** | `House: Property Info Added` | User adds a new item to Property Info. | `info_type` |

### 6.4. "Life" Tab Events

These events measure how users engage with the high-level dashboard of their household's activity, tracking their journey from summary to detail.

| Priority | Event Name | Trigger | Properties |
| :---- | :---- | :---- | :---- |
| **P1** | `Life Tab: Viewed` | User navigates to the "Life" tab. |  |
| **P1** | `Life Tab: Drill Down` | User taps a card in "Weekly Stats" or "Everyone's Stuff". | `section`, `item_type` |
| **P1** | `Life Tab: Member Tapped` | User taps on a specific Hive member. |  |

### 6.5. Subscription Events

These events track the monetization funnel, measuring a user's journey from expressing interest in a paid plan to becoming a subscriber.

| Priority | Event Name | Trigger | Properties |
| :---- | :---- | :---- | :---- |
| **P1** | `Subscription: Purchase Started` | User taps on a "subscribe"button | `plan_name`, `source` |
| **P1** | `Subscription: Purchase Completed` | User successfully completes a purchase. | `plan_name` |
| **P1** | `Subscription: Purchase Failed` | A purchase attempt fails. | `failure_reason` |

# 7\. Property Dictionary

This section defines every custom property used in the event tables above.

| Property Name | Type | Description | Example Values |
| :---- | :---- | :---- | :---- |
| appliance\_type | String | The specific type of appliance being added to a House. | `Fridge`, `Washing_machine`, `Oven` |
| assignee\_type | String | The type of entity a task is assigned to. | `hive_member`, `contact` |
| creator\_user\_id | String | The unique identifier of the user who originally created the DENT being acted upon. |  |
| entry\_point | String | Where the user started their sign-up journey from. | `app_store`, `website_promo`, `user_invite_link` |
| error\_message | String | The system-generated error message shown to the user on a failed action. | `Invalid credentials`, `An unknown error occurred` |
| file\_type | String | The file extension of an uploaded document. | `.pdf`, `.jpg`, `.docx` |
| info\_type | String | The specific type of property information being added to a House. | `Mortgage`, `Insurance`, `Taxes` |
| is\_recurring | Boolean | Identifies if a task is set to repeat. | `true`, `false` |
| item\_type | String | The category of item drilled down into on the "Life" tab. | `Incomplete Tasks`, `Notes`, `Events` |
| login\_method | String | The authentication method used to log in. | `email`, `google`, `apple` |
| new\_role | String | The new role assigned to a Hive member. | `admin`, `active_member`, `passive_member` |
| plan\_name | String | The name of the subscription plan being purchased. | `premium_monthly`, `premium_yearly` |
| section | String | The section on the "Life" tab that was interacted with. | `Weekly Stats`, `Everyone's Stuff` |
| signup\_method | String | The authentication method used to create an account. | `email`, `google`, `apple` |
| source | String | The UI element or screen from where the subscription flow was initiated. | `settings_page`, `upgrade_prompt_modal` |
| space\_type | String | The specific type of space being added to a House. | `Kitchen`, `Basement`, `Attic` |
| tile\_name | String | The name of the House or category tile tapped on the home screen. | `Kitchen`, `Garage`, `Appliances` |
| utility\_type | String | The specific type of utility being added to a House. | `Electricity`, `Water`, `Internet` |

### 

## 7\. Session Replay (Post-Launch Follow-Up)

**Note:** This is **not a requirement for the initial launch**, but should be considered a high-priority item.

In addition to event-based tracking, we should implement Session Replay. This will allow us to watch video-like recordings of user sessions, helping us understand where users get stuck, confused, or frustrated. This is the perfect tool to answer the "why" behind the quantitative data and is critical for our goal of learning from the Dragon's Den launch traffic.

https://amplitude.com/docs/session-replay/instrument-session-replay

## 8\. Out of Scope

The following items are explicitly out of scope for this *initial* implementation:

* A/B testing framework integration.  
* Marketing attribution (e.g., tracking ad campaign sources).  
* Advanced e-commerce tracking (e.g., LTV).

