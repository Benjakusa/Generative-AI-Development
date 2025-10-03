"""Token Generator System with Payment Processing"""

import random
import sqlite3
from datetime import datetime, timedelta

walker TokenGenerator {
    has account_number: str;
    has amount: float;
    has token: str = "";
    has operation: str;  # "generate", "validate", "use", "info"
    has input_token: str = "";
    
    can start with `root entry;
    can process_payment with payment_node entry;
    can validate_token with validation_node entry;
    can use_token with usage_node entry;
    can get_account_info with info_node entry;
}

node payment_node {
    has account_number: str;
    has amount: float;
    has status: str = "pending";
    has generated_token: str = "";
}

node validation_node {
    has account_number: str;
    has token: str;
    is_valid: bool = false;
    has message: str = "";
}

node usage_node {
    has account_number: str;
    has token: str;
    has success: bool = false;
    has message: str = "";
}

node info_node {
    has account_number: str;
    has balance: float = 0.0;
    has tokens: list = [];
}

node database_node {
    has db_name: str = "token_system.db";
}

# Database initialization function
def init_database() {
    conn = sqlite3.connect("token_system.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_number TEXT PRIMARY KEY,
            balance REAL DEFAULT 0.0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            account_number TEXT,
            amount_paid REAL,
            is_used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (account_number) REFERENCES accounts (account_number)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT,
            amount REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_number) REFERENCES accounts (account_number)
        )
    ''')
    
    conn.commit()
    conn.close()
}

def create_account(account_number: str, initial_balance: float = 0.0) -> bool {
    conn = sqlite3.connect("token_system.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO accounts (account_number, balance) VALUES (?, ?)",
            (account_number, initial_balance)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
}

def generate_unique_token(account_number: str, amount: float) -> str {
    conn = sqlite3.connect("token_system.db")
    cursor = conn.cursor()
    
    while True:
        token = str(random.randint(1000000000, 9999999999))
        
        cursor.execute("SELECT token FROM tokens WHERE token = ?", (token,))
        if not cursor.fetchone():
            break
    
    expires_at = datetime.now() + timedelta(hours=24)
    
    cursor.execute(
        "INSERT INTO tokens (token, account_number, amount_paid, expires_at) VALUES (?, ?, ?, ?)",
        (token, account_number, amount, expires_at)
    )
    
    conn.commit()
    conn.close()
    
    return token
}

def validate_token_in_db(token: str, account_number: str) -> dict {
    conn = sqlite3.connect("token_system.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT token, account_number, is_used, expires_at 
        FROM tokens 
        WHERE token = ? AND account_number = ?
    ''', (token, account_number))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return {"valid": False, "message": "Invalid token or token doesn't belong to this account"}
    
    token, account, is_used, expires_at = result
    
    if is_used:
        return {"valid": False, "message": "Token has already been used"}
    
    if datetime.now() > datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S'):
        return {"valid": False, "message": "Token has expired"}
    
    return {"valid": True, "message": "Token is valid"}
}

def use_token_in_db(token: str, account_number: str) -> dict {
    validation = validate_token_in_db(token, account_number)
    if not validation["valid"]:
        return validation
    
    conn = sqlite3.connect("token_system.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE tokens SET is_used = TRUE WHERE token = ? AND account_number = ?",
        (token, account_number)
    )
    
    conn.commit()
    conn.close()
    
    return {"valid": True, "message": f"Token {token} has been successfully used and marked as consumed"}
}

def get_account_info_from_db(account_number: str) -> dict {
    conn = sqlite3.connect("token_system.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM accounts WHERE account_number = ?", (account_number,))
    account_result = cursor.fetchone()
    
    if not account_result:
        return {"found": False, "message": "Account not found"}
    
    cursor.execute('''
        SELECT token, amount_paid, is_used, created_at, expires_at 
        FROM tokens 
        WHERE account_number = ? 
        ORDER BY created_at DESC
    ''', (account_number,))
    
    tokens = cursor.fetchall()
    conn.close()
    
    return {
        "found": True,
        "account_number": account_number,
        "balance": account_result[0],
        "tokens": tokens
    }
}

def simulate_payment_gateway(account_number: str, amount: float) -> bool {
    return amount > 0
}

# Initialize database and create demo accounts
init_database()
create_account("ACC001", 100.0)
create_account("ACC002", 50.0)

# CLI Entry Point
with entry:__main__ {
    # Demo operations
    root spawn TokenGenerator(
        account_number="ACC001", 
        amount=25.0, 
        operation="generate"
    );
    root spawn TokenGenerator(
        account_number="ACC001", 
        operation="info"
    );
}

impl TokenGenerator.start {
    # Initialize database connection node if not exists
    if not [root --> (`?database_node)] {
        next = root ++> database_node("token_system.db");
    } else {
        next = [root --> (`?database_node)];
    }
    
    # Route based on operation type
    if self.operation == "generate" {
        payment_node = here ++> payment_node(
            account_number=self.account_number, 
            amount=self.amount
        );
        visit payment_node;
    } elif self.operation == "validate" {
        validation_node = here ++> validation_node(
            account_number=self.account_number,
            token=self.input_token
        );
        visit validation_node;
    } elif self.operation == "use" {
        usage_node = here ++> usage_node(
            account_number=self.account_number,
            token=self.input_token
        );
        visit usage_node;
    } elif self.operation == "info" {
        info_node = here ++> info_node(account_number=self.account_number);
        visit info_node;
    } else {
        print("Invalid operation");
        disengage;
    }
}

impl TokenGenerator.process_payment {
    # Process payment and generate token
    if simulate_payment_gateway(here.account_number, here.amount):
        # Update account balance in database
        conn = sqlite3.connect("token_system.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT balance FROM accounts WHERE account_number = ?", (here.account_number,))
        current_balance = cursor.fetchone()[0]
        new_balance = current_balance + here.amount
        
        cursor.execute(
            "UPDATE accounts SET balance = ? WHERE account_number = ?",
            (new_balance, here.account_number)
        )
        
        # Record payment
        cursor.execute(
            "INSERT INTO payments (account_number, amount, status) VALUES (?, ?, ?)",
            (here.account_number, here.amount, 'COMPLETED')
        )
        
        conn.commit()
        conn.close()
        
        # Generate token
        generated_token = generate_unique_token(here.account_number, here.amount)
        here.generated_token = generated_token
        here.status = "completed"
        
        print(f" Payment processed successfully!")
        print(f" Account: {here.account_number}")
        print(f" Amount: ${here.amount}")
        print(f" Generated Token: {generated_token}")
        print(f" New Balance: ${new_balance}")
    else:
        here.status = "failed"
        print(f" Payment failed for account {here.account_number}")
    
    disengage;
}

impl TokenGenerator.validate_token {
    validation_result = validate_token_in_db(here.token, here.account_number)
    here.is_valid = validation_result["valid"]
    here.message = validation_result["message"]
    
    if here.is_valid:
        print(f"{here.message}")
    else:
        print(f"{here.message}")
    
    disengage;
}

impl TokenGenerator.use_token {
    usage_result = use_token_in_db(here.token, here.account_number)
    here.success = usage_result["valid"]
    here.message = usage_result["message"]
    
    if here.success:
        print(f"{here.message}")
    else:
        print(f" {here.message}")
    
    disengage;
}

impl TokenGenerator.get_account_info {
    account_info = get_account_info_from_db(here.account_number)
    
    if not account_info["found"]:
        print(" Account not found")
        disengage;
    
    here.balance = account_info["balance"]
    here.tokens = account_info["tokens"]
    
    print(f"\n📊 Account Information:")
    print(f"Account: {here.account_number}")
    print(f"Balance: ${here.balance}")
    print(f"\nTokens:")
    
    for token in here.tokens:
        token_str, amount, is_used, created, expires = token
        status = "USED" if is_used else "ACTIVE"
        print(f"  Token: {token_str} | Amount: ${amount} | Status: {status} | Created: {created}")
    
    disengage;
}
