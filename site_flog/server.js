// 【統合時メモ・現在未使用】
// API配信・Web画面配信は server/app.py (Python/Flask) に一本化しました。
// このNode.js版は実行しません。参考実装として残しています。
const express = require("express");
const http = require("http");
const { Server } = require("socket.io");

const { SerialPort } = require("serialport");
const { ReadlineParser } = require("@serialport/parser-readline");

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.static("./"));

const port = new SerialPort({
    path: "COM4",     // ←あとでArduinoのCOM番号に変更
    baudRate: 9600
});

const parser = port.pipe(new ReadlineParser());

let can = 0;
let bottle = 0;
let pet = 0;

parser.on("data", (data) => {

    data = data.trim();

    console.log(data);

    if(data === "CAN"){
        can++;
    }

    if(data === "BOTTLE"){
        bottle++;
    }

    if(data === "PET"){
        pet++;
    }

    io.emit("update",{
        can:can,
        bottle:bottle,
        pet:pet
    });

});
app.get("/reset",(req,res)=>{

    can=0;
    bottle=0;
    pet=0;

    io.emit("update",{
        can,
        bottle,
        pet
    });

    res.send("OK");

});
server.listen(3000, () => {
    console.log("Server Start");
});