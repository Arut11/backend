from flask import Flask, request, jsonify
import psycopg2
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Функция для создания соединения с базой данных и возвращения соединения и курсора
def get_db_connection():
    conn = psycopg2.connect(
        database="habrdb",
        user="habrpguser",
        password="123456",
        host="habr-pg-13.3",
        port="5432"
    )
    return conn, conn.cursor()




                                    # удаление заказа по номеру заказа
@app.route('/orders/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    try:
        conn, cur = get_db_connection()

        cur.execute('DELETE FROM order_item WHERE order_id = %s', (order_id,))
        conn.commit()

        cur.execute('DELETE FROM orders WHERE order_id = %s RETURNING order_id', (order_id,))
        deleted_order_id = cur.fetchone()
        if not deleted_order_id:
            conn.close()
            response = jsonify({"message": "Заказ не найден"})
            response.status_code = 400
            return response
        conn.commit()

        conn.close()
        return jsonify({"message": "Заказ успешно удален"})
    except psycopg2.Error as e:
        return jsonify({"message": "Ошибка при удалении заказа"})





                                                # Официант
@app.route('/waiter', methods=['POST'])
def create_waiter():
    try:
        conn, cur = get_db_connection()

        table_number = request.json['table_number']

        if 'call_waiter' in request.json:
            cur.execute('INSERT INTO waiter (table_number, call_waiter, score) VALUES(%s, %s, %s)',
                        (table_number, 1, 0))  # передача 1 означает вызов официанта

        if 'score' in request.json:
            cur.execute('INSERT INTO waiter (table_number, call_waiter, score) VALUES(%s, %s, %s)',
                        (table_number, 0, 1))  # передача 2 означает запрос счета

        conn.commit()
        conn.close()
        return jsonify({"message": "Официант скоро будет"})
    except psycopg2.Error as e:
        return jsonify({"message": "Ошибка при вызове"})




                                             # Создание нового заказа
@app.route('/orders', methods=['POST'])
def create_order():
    try:
        conn, cur = get_db_connection()

        # Проверяем, есть ли уже заказы в таблице orders
        cur.execute('SELECT MAX(order_id) FROM orders')
        max_order_id = cur.fetchone()[0]

        if max_order_id is None:
            order_id = 1
        else:
            order_id = max_order_id + 1

        # Создаем новый заказ
        table_number = request.json['table_number']
        order_price = request.json['order_price']
        order_comment = request.json['order_comment']
        cur.execute('INSERT INTO orders (order_id, table_number, order_status, order_price, order_comment) VALUES (%s, %s, %s, %s, %s)',
                    (order_id, table_number, 1, order_price, order_comment))

        # Добавляем позиции в заказ
        items = request.json['items']
        for item in items:
            dish_id = item['dish_id']
            quantity = item['quantity']
            cur.execute('INSERT INTO order_item (order_id, dish_id, quantity) VALUES (%s, %s, %s)',
                        (order_id, dish_id, quantity))

        conn.commit()
        conn.close()

        response_data = {
            'order_id': order_id
        }
        return json.dumps(response_data)
    except psycopg2.Error as e:
        response_data = {
            'error': str(e),
            'message': 'Произошла ошибка при создании заказа: {}'.format(str(e))
        }
        return json.dumps(response_data)





@app.route('/orders/<order_status>', methods=['GET'])
def get_order_info(order_status):
    try:
        cur = get_db_connection()

        cur.execute('SELECT orders.order_id, orders.table_number, dish.dish_name, orders.order_status, dish.price, order_item.quantity, orders.order_comment, orders.order_price FROM orders JOIN order_item ON orders.order_id = order_item.order_id JOIN dish ON order_item.dish_id = dish.dish_id WHERE orders.order_status = %s', (order_status,))
        result = cur.fetchall()
        if not result:
            return jsonify({"error": "Заказы с указанным статусом не найдены"}), 400

        orders = {}
        for row in result:
            order_id, table_number, dish_name, order_status, price, quantity, order_comment, order_price = row
            if order_id not in orders:
                orders[order_id] = {
                    "order_price": order_price,
                    "order_comment": order_comment,
                    "order_id": order_id,
                    "table_number": table_number,
                    "order_status": order_status,
                    "items": []
                }
            order = orders[order_id]
            order["items"].append({
                "dish_name": dish_name,
                "price": price,
                "quantity": quantity
            })

        return jsonify(orders)
    except psycopg2.Error as e:
        response_data = {
            'error': str(e),
            'message': 'Произошла ошибка при получении информации о заказе: {}'.format(str(e))
        }
        return json.dumps(response_data)

if __name__ == '__main__':
    app.config['DEBUG'] = True
    app.run(host='0.0.0.0', port=5000, debug=True)