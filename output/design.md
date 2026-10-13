# Campus Customs Dashboard Design

## Visual direction

The dashboard uses a bright, white operations-desk look with deep navy text and clear blue action states. Blue communicates trust and control, while small cyan, violet, amber, and rose accents distinguish the five agent roles without turning the board into a noisy rainbow.

## Layout and behavior

- A compact top bar identifies the shop and keeps the reset action available.
- The opening area pairs a simple “next right call” message with a prominent checking-balance card.
- The left rail lists all tickets with ID, requester, type, status, and selection state.
- The main console shows the selected ticket, a single Start agent team action, live status, and a chronological agent activity feed.
- The frontend polls `/events` while the team runs, so each agent step and MCP lookup appears as the backend appends it.

## Human clarity and safety

Agent names are shown as readable labels with role-colored avatars. Tool calls appear as small evidence chips, while the “Human approval required” indicator stays visible beside the run status. Resolved tickets turn green and disable the run button. The checking balance is always visible and refreshes after an approval.

Payment and purchase approval controls are reserved for the backend approval flow; agents only prepare recommendations. The dashboard never sends customer or vendor messages.

## What makes it enjoyable

The “next right call” framing makes the board feel like a calm control room rather than an intimidating admin panel. Small details—the sparkle mark, generous spacing, live pulse, and concise event language—make the team feel present and understandable while keeping the human in charge.
