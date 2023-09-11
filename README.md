# Instalación contenedor de mongoDB con Docker
```bash
docker pull mongodb/mongodb-community-server
docker run --name mongo -d mongodb/mongodb-community-server:latest
```
Se obtiene la siguiente URI que será ingresada tanto en MongoDB Compass como en la APP con Flask para la conexión
```bash
mongodb://172.17.0.2:27017/
```

# Recuperación y almacenamiento de información en MongoDB
1. Instalación de MongoDB Compass para visualización de la base de datos.
2. Instalación de herramientas para recuperar las bases de datos desde el repositorio y guardarlas en la implementación local usando [database-tools](https://www.mongodb.com/docs/database-tools/installation/installation-linux/)

3. Se usa [mongodump](https://www.mongodb.com/docs/database-tools/mongodump/) el cual es una utilidad que crea una exportación binaria del contenido de una base de datos para ser almacenado en local.
* Se descaga la base de datos *FHIRGenomicsData* con el siguiente comando
```bash
mongodump --uri mongodb+srv://download:download@cluster0.8ianr.mongodb.net/FHIRGenomicsData
```

* Se descaga la base de datos *UtilitiesData* con el siguiente comando
```bash
mongodump --uri mongodb+srv://download:download@cluster0.8ianr.mongodb.net/UtilitiesData
```

5. Se carga la información en la implementación de mongoDB local usando el comando [mongorestore](https://www.mongodb.com/docs/database-tools/mongorestore/)

```bash
mongorestore --uri="mongodb://172.17.0.2:27017/"
```

# Clonación del repositorio de código
```bash
git clone --recurse-submodules https://github.com/FHIR/genomics-operations.git
```

# Configuración del entorno de trabajo
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

# Ejecutar con el siguiente comando
```bash
flask --app app run --debug
```