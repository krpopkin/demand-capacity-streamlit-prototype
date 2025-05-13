# DC (Demand-Capacity)

A lightweight, portfolio-level resource management tool built with Streamlit and PostgreSQL.

---

## Table of Contents

- [Overview](#overview)  
- [Prerequisites & Dependencies](#prerequisites--dependencies)  
- [Installation & Setup](#installation--setup)  
- [Configuration](#configuration)  
- [Usage](#usage)  
- [Database Schema](#database-schema)  
- [Soft Delete & Activation](#soft-delete-activation)  
- [Deployment](#deployment)  
- [Bulk-Load Routines](#bulk-load-routines)  
- [Tests](#tests)  
- [License & Contributing](#license--contributing)  

---

## Overview

DC (Demand-Capacity) helps you:

- **Reports**  
  1. View demand per product by role  
  2. View capacity (allocations) per team member across products  

- **Demand**  
  - **Products** tab – manage product name, product manager, and executive sponsor  
  - **Assignments** tab – assign team members to products with allocation %  

- **Capacity**  
  - **Roles** tab – define portfolio roles  
  - **Team Members** tab – list team members  
  - **Skills Matrix** tab – designate team-member skill level (beginner, intermediate, expert) for each role  

---

## Prerequisites & Dependencies

- **Python** 3.x  
- **PostgreSQL** database (hosted on GCP)  
- **Docker** (for deployment to Cloud Run)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Contents of `requirements.txt`:

```
streamlit
pandas
sqlalchemy
psycopg2-binary
streamlit-aggrid
xlsxwriter
```

---

## Installation & Setup

1. **Clone the repo**  
   ```bash
   git clone https://github.com/<your-org>/dc.git
   cd dc
   ```

2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your database credentials**  
   - Edit `db.py` and replace the dummy values with your actual `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`.  
   - **Do not commit real credentials!**

4. **Run locally**  
   ```bash
   streamlit run app.py
   ```

---

## Configuration

All connection/config settings live in **db.py**. It contains placeholders—reach out to Ken Popkin for the real values.

```python
DB_HOST = "your-db-host"
DB_PORT = "5432"
DB_USER = "your-db-user"
DB_PASSWORD = "your-db-password"
DB_NAME = "your-db-name"
```

---

## Usage

- **Locally:** open `http://localhost:8501`  
- **Deployed:** use the Cloud Run URL (contact Ken Popkin for the link)

---

## Database Schema

### `assignments`
| column_name    | data_type                   |
|----------------|-----------------------------|
| id             | integer                     |
| product_id     | integer                     |
| role_id        | integer                     |
| teammember_id  | integer                     |
| allocation     | numeric                     |
| is_active      | boolean                     |
| created_at     | timestamp without time zone |

### `skills_matrix`
| column_name     | data_type                   |
|-----------------|-----------------------------|
| id              | integer                     |
| teammembers_id  | integer                     |
| role_id         | integer                     |
| created_at      | timestamp without time zone |
| skill_level     | text                        |

### `products`
| column_name           | data_type                   |
|-----------------------|-----------------------------|
| id                    | integer                     |
| created_at            | timestamp without time zone |
| name                  | text                        |
| manager               | text                        |
| technology_executive  | text                        |

### `roles`
| column_name    | data_type                   |
|----------------|-----------------------------|
| id             | integer                     |
| created_at     | timestamp without time zone |
| name           | text                        |
| description    | text                        |

### `team_members`
| column_name    | data_type                   |
|----------------|-----------------------------|
| id             | integer                     |
| created_at     | timestamp without time zone |
| name           | text                        |
| manager        | text                        |
| level          | text                        |

---

## 🛡️ Soft-Delete & Auto-Inactivation Rules

We never hard-delete rows—instead we mark them inactive (`is_active = FALSE`) and automatically propagate that inactivation to dependent records:

1. **Teammember Inactivation**  
   When a **teammember** is set to inactive, all of their related rows in both the `assignments` and `skills_matrix` tables are also marked inactive.

2. **Role Inactivation**  
   When a **role** is set to inactive, any entries in `skills_matrix` for that role—and any rows in `assignments` where that role was assigned—are marked inactive.

3. **Product Removal**  
   When a **product** is deleted (or inactivated), all `assignments` referencing that product are marked inactive.

---

## Deployment

A simple shell script handles build & deploy:

```bash
./deploy.sh
```

This builds the Docker image and deploys to GCP Cloud Run under your project.

---

## Bulk-Load Routines

CSV bulk-load scripts live in the `data_to_load/` folder for:

- Products  
- Roles  
- Team Members  

Run them as needed to seed your database.

---

## Tests

*No automated tests are currently provided.*

---

## License & Contributing

*No license specified.*  
*No CONTRIBUTING guidelines defined.*
