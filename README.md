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
