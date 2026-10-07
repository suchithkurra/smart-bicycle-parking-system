from app import create_app

app = create_app()

if __name__ == "__main__":
    # host="0.0.0.0" lets other devices on the network (e.g. a phone) open the dashboard
    app.run(host="0.0.0.0", port=8001, debug=True)
