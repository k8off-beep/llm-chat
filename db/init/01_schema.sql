CREATE TABLE products (
    id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL
);

COMMENT ON TABLE products IS 'таблица продуктов';
COMMENT ON COLUMN products.name IS 'уникальное название товара';
COMMENT ON COLUMN products.category IS 'категория продукта';

CREATE TABLE sales (
    id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sale_date DATE NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    amount NUMERIC(14, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

COMMENT ON TABLE sales IS 'строка sales — это не заказ, а завершённая продажа одного товара в определённую дату';
COMMENT ON COLUMN sales.product_id IS 'ссылка на products.id. название и категорию товара брать через JOIN products ON products.id = sales.product_id';
COMMENT ON COLUMN sales.sale_date IS 'дата продажи. период: sale_date >= начало AND sale_date < конец (конец не включается)';
COMMENT ON COLUMN sales.quantity IS 'количество проданных единиц. проданные единицы = SUM(quantity)';
COMMENT ON COLUMN sales.unit_price IS 'цена одной единицы в рублях на момент продажи';
COMMENT ON COLUMN sales.amount IS 'вычисляемая сумма продажи в рублях: quantity * unit_price. Выручка = SUM(amount)';