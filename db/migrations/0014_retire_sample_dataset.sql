-- Retire the vendor sample dataset (Saudi lubricants / PET-001…) that shipped with
-- the template. The seed loader only upserts by id and never deletes, so after a
-- tenant switches its db/seed files the old rows would keep answering customers.
-- Idempotent: only the exact sample ids are touched; tenant-authored rows survive.
-- Rows are deactivated (not deleted) so historical quotes/orders keep their FKs.

UPDATE products SET is_active = FALSE, updated_at = NOW()
WHERE id IN (
    '96132c95-b2f2-53cd-989c-59e27fb449b3',
    '3dbb2197-5e42-553a-93a5-729379a8188e',
    '2024c1d6-76e3-53ce-bf84-5e1f54d0f066',
    'f994f2e3-9b6a-50ad-aa31-9e769629b2ce',
    '874c53f7-a938-56e5-b054-9e75a50ffa25'
) AND is_active = TRUE;

UPDATE faq SET is_active = FALSE
WHERE id IN (
    '48b762a1-7aab-5cb6-b556-9ecf79d942e7',
    'd1890195-aaf0-5b17-9e1c-4c063def56d7',
    '3777be34-eb43-55a4-9024-d914a2a07c70'
) AND is_active = TRUE;

UPDATE troubleshooting SET is_active = FALSE
WHERE id IN (
    '1e29036e-1494-5763-bf8f-f3990afe9c7f',
    '9cfbcd83-4cc4-590a-98b0-1262ebb56cbd',
    '8c2fb416-698a-5909-aa75-518e4439ddb2'
) AND is_active = TRUE;
