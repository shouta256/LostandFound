# Lost and Found

> A searchable app that lets students and campus offices post found items or search for lost ones — so items stop ending up forgotten in a drawer.

## Overview

Lost items (AirPods, IDs, water bottles) end up in a random office drawer nobody checks, and people just give up looking. This web application helps reunite lost items with their owners by providing a centralized platform for reporting and searching for lost and found items on campus.

## Features

- **Post Found Items** - Students and campus offices can create listings for items they have found.
- **Search Lost Items** - Users can search for lost items using information such as item name, category, location, or date.
- **Item Details** - Users can view important information about a lost or found item.
- **Report Lost Items** - Students can provide information about items they have lost.
- **Manage Listings** - Users can update or remove their own lost and found listings.
- **Item Status** - Listings can be updated when an item has been returned to its owner.
- **Campus-Focused Search** - The system is designed specifically to help students and campus offices manage lost and found items.

## Getting Started

### Prerequisites

- Git (for cloning the repository)
- Node.js and npm (for running the application)
- A modern web browser (Chrome, Firefox, Safari, or Edge)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/shouta256/LostandFound.git
cd LostandFound
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The application will open in your browser at `http://localhost:3000`.

### Usage

1. **Browse Found Items** - Visit the homepage to see all items that have been found
2. **Report a Lost Item** - Click "Report Lost Item" and fill in details about your missing item
3. **Post a Found Item** - Click "Post Found Item" if you've found something and want to help return it
4. **Search for Items** - Use the search bar to filter items by name, category, location, or date
5. **Contact Owner** - View item details and contact information to claim your lost item

## Project Structure

```
.
├── src/              # Application source code
│   ├── components/   # React components
│   ├── pages/        # Page components
│   └── App.js        # Main application component
├── public/           # Static assets
├── tests/            # Automated tests
├── .git/             # Git repository
├── package.json      # Project dependencies and scripts
├── README.md         # This file
└── GITHUB_GUIDE.md   # Git workflow guide for contributors
```

## Configuration

Environment variables and configuration are managed through:
- `.env` file for local development settings
- Environment variables for production deployment

No special configuration is required for the initial setup. The application uses default settings for development.

## Contributing

New to GitHub? Read the [GitHub Beginner Guide](GITHUB_GUIDE.md) for the clone, edit, commit, and push workflow.

### Contributing Steps

1. Create a branch for your change (`git switch -c feature-name`)
2. Make and test your changes locally
3. Commit your changes with a clear message (`git commit -m "Description of change"`)
4. Push your branch to GitHub (`git push -u origin feature-name`)
5. Open a pull request with a clear description of your changes
6. Respond to any feedback from code reviewers
7. Once approved, your pull request will be merged into main

For detailed instructions, see the [GitHub Beginner Guide](GITHUB_GUIDE.md).

## License

This project is created for educational purposes as part of the CM 333 course at Washburn University.
