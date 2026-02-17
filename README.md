🚗 Car Market & ERP System

A full-featured Online Car Marketplace + Enterprise Resource Planning (ERP) system built with Django & Django REST Framework, designed to manage vehicle sales, dealership operations, accounting, HR, and business workflows in one unified platform.

📌 Overview

This system combines:

🛒 Online Car Marketplace

🏢 Dealer & Broker Management

💼 ERP Modules (HR, Payroll, Accounting, Sales)

🔔 Real-time Notifications

📊 Analytics & Reporting

🔐 Role-Based Access Control (RBAC)

It enables car dealers to manage inventory and sales, brokers to handle leads, buyers to purchase vehicles, and admins to oversee the entire system.

🏗️ System Architecture
Client (React / Browser / Mobile)
        ↓
Django REST API
        ↓
Business Logic Layer (Services)
        ↓
PostgreSQL Database
        ↓
Real-time Layer (Django Channels - WebSockets)

🚀 Core Features
🛒 Marketplace Module

Car listing (make, model, year, price, body type, sale type)

Multiple car images

Featured vehicles

Car verification workflow

Lead management

Car analytics

Saved cars

Ad interaction tracking (View, Like, Click, Save)

👥 User Roles

Admin

Dealer

Dealer Staff

Broker

Sales Agent

Buyer

Accountant

HR

Role-based permissions ensure proper system access.

📈 Sales & Lead Management

Lead creation & assignment

Lead status tracking

Sales closing workflow

Commission tracking

Dealer dashboard analytics

Broker performance tracking

🏢 ERP Modules
💰 Accounting

Income & expense tracking

Employee salary management

Payroll processing

Financial reports

👨‍💼 HR

Employee management

Payroll

Salary records

Role assignment

🔔 Notifications

Real-time notifications using Django Channels

Car posted alerts

Lead updates

Status change alerts

Unread notification filtering

📊 Analytics & Reporting

Leads analytics

Sales performance

Car performance metrics

Revenue reports

Broker activity reports

🛠️ Tech Stack
Backend

Django

Django REST Framework

PostgreSQL

Django Channels

JWT Authentication

Deployment

Render

Neon

API Testing

Insomnia

📂 Project Structure (Simplified)
api/
accounts/
cars/
leads/
sales/
hr/
accounting/
notifications/
analytics/


Each module follows clean architecture principles:

Models

Serializers

Views / ViewSets

Services (Business Logic Layer)

Permissions

Signals (where needed)

🔐 Authentication

JWT-based authentication

Role-based permission system

Secure endpoints per user type

Example:

POST /api/accounts/login/
GET  /api/cars/
POST /api/dealers/cars/
PATCH /api/sales/leads/{id}/update_status/

📦 Installation
1️⃣ Clone Repository
git clone https://github.com/your-username/car-market-erp.git
cd car-market-erp

2️⃣ Create Virtual Environment
python -m venv myenv
source myenv/bin/activate  # Linux

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Configure Environment Variables

Create .env file:

DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=your_database_url

5️⃣ Run Migrations
python manage.py migrate

6️⃣ Run Server
python manage.py runserver

🌐 Deployment

The system is deployed on:

Backend: Render

Database: Neon PostgreSQL

Production configuration includes:

Environment variables

Static file handling

Database connection pooling

Secure secret management

📊 API Documentation

API documentation is generated using:

drf-spectacular (OpenAPI / Swagger)

Access:

/api/schema/
/api/docs/

🧠 Business Logic Design

The system follows:

Service-layer architecture

Atomic transactions for financial operations

Row-level locking for sensitive workflows

Idempotent verification logic

Soft deletes where required

👨‍💻 Author

Erdey Syoum
Senior Backend Developer
Python | Django | ERP Systems | Marketplace Systems

📄 License

This project is licensed under the MIT License.
