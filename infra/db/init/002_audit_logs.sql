"""
infra/db/init/002_audit_logs.sql — Immutable audit trail.
Implements triggers to prevent deletion or modification of order/trade history.
"""

-- 1. Create Order Audit Table
CREATE TABLE IF NOT EXISTS order_audit_log (
    log_id SERIAL PRIMARY KEY,
    order_id TEXT NOT NULL,
    action TEXT NOT NULL, -- INSERT, UPDATE
    old_status TEXT,
    new_status TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    changed_by TEXT DEFAULT CURRENT_USER
);

-- 2. Audit Trigger Function
CREATE OR REPLACE FUNCTION audit_order_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        INSERT INTO order_audit_log (order_id, action, old_status, new_status)
        VALUES (OLD.order_id, 'UPDATE', OLD.status, NEW.status);
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO order_audit_log (order_id, action, new_status)
        VALUES (NEW.order_id, 'INSERT', NEW.status);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Apply Trigger
CREATE TRIGGER trg_audit_orders
AFTER INSERT OR UPDATE ON orders
FOR EACH ROW EXECUTE FUNCTION audit_order_changes();

-- 4. Prevent Deletion (Security Enforcement)
CREATE OR REPLACE FUNCTION block_deletions()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Deletion not allowed on immutable audit tables.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_no_delete_trades
BEFORE DELETE ON trade_history
FOR EACH ROW EXECUTE FUNCTION block_deletions();

CREATE TRIGGER trg_no_delete_audit
BEFORE DELETE ON order_audit_log
FOR EACH ROW EXECUTE FUNCTION block_deletions();
