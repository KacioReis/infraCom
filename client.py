import socket
import json
import sys
import select
import time

millis_now = lambda: int(round(time.time() * 1000))

def printMenu():
	print("***** MENU *****")
	print("1. Ver lista de arquivos disponíveis no server")
	print("2. Download de arquivo")
	print("3. Encerrar")
	
def printArchives(localArchives):
	print("***** ARQUIVOS DISPONIVEIS *****")
	for i in localArchives:
		print(i)

def sendRequest(localArchives, dest):
	'''
	Envia requisição de arquivo desejado para o server
	
	param localArchives      Lista de arquivos disponíveis no server
	param dest               Informações sobre o host de destino
	'''
	while 1:
		print("Nome do arquivo?")
		arqName = input()
		try:
			isNum = (int(arqName) >= 0 and int(arqName) < len(localArchives))
		except:
			pass
	
		if arqName in localArchives:
			requestMessage = {
				"type": "request", 
				"request": arqName
			}
			send_message(clientSocket,dest,requestMessage)
			#clientSocket.sendto(bytes(json.dumps(requestMessage), encoding='latin-1'), dest)
			
			# TODO: Adicionar uma espera para a resposta do server
			
			break
		else:
			print("Arquivo não encontrado :(")
	
def connect_to_server(clientSocket, dest):
	'''
	Configura o inicio da conexão com uma
	lista de arquivos disponíveis no servidor
	no momento da conexão
	
	param clientSocket       Socket aberto para trafego UDP
	param dest               Informações sobre o host de destino
	'''
	MAX_TIMEOUT = 20000
	TIMEOUT = 1000
	begin = millis_now()
	time = millis_now()
	recv = False
	localArchives = []
	
	connectMessage = {
		"type": "connect"
	}
	
	# send message
	clientSocket.sendto(bytes(json.dumps(connectMessage), encoding='latin-1'), dest)
	
	while not recv:
		if millis_now() - begin > MAX_TIMEOUT:
			print("timeout")
			break
		
		elif millis_now() - time <= TIMEOUT:
			try:
				msg, server = clientSocket.recvfrom(1024)
				msgJSON = json.loads(msg)
				print(msgJSON)
							
				if msgJSON["type"] == "archives":
					localArchives = msgJSON["archives"]
					recv = True
					#recibir a mensagem tá ok agora 
					msgSucesse = {
						"type": "OK"
					}
					clientSocket.sendto(bytes(json.dumps(msgSucesse), encoding='latin-1'), dest)
					break
			except:
				pass
			
		else: # pacote perdido reenvia
			clientSocket.sendto(bytes(json.dumps(connectMessage), encoding='latin-1'), dest)
			time = millis_now()
			pass
	
	return recv, localArchives

def send_message(clientSocket, dest, msg):
	'''
	Uma interface de envio de mensagem de stream,
	assumindo que a stream pode ter um tamanho qualquer.
	
		param clientSocket   Socket aberto para trafego UDP
		param dest           Informações sobre o host de destino
		param msgList        Uma mensagem que deve ser enviada para o server.
		                     Esta mensagem deve ser um JSON contendo a informação
		                     desejada de envio.
		
		returns              Uma tupla (status, respostas) com uma lista de
		                     respostas do servidor para cada um dos pacotes
		                     enviados pelo client.
	'''
	
	MAX_TIMEOUT = 20000
	TIMEOUT = 1000
	begin = millis_now()
	time = millis_now()
	
	resend = False
	recv = False
	recvFirst = False
	msgCount = 0
	
	timer = 0
	ans = []
	
	# send message
	clientSocket.sendto(bytes(json.dumps(msg), encoding='latin-1'), dest)
	
	while not recv:
		# quebra aqui caso passe muito tempo sem receber mensagens
		if millis_now() - begin > MAX_TIMEOUT:
			break
		
		elif millis_now() - time <= TIMEOUT:
			try:
				msg, server = clientSocket.recvfrom(1024)
				msgJSON = json.loads(msg)
				
				# TODO: Check every message type, if error message then resend, 
				# otherwise, then go over the new package and threat it
				# no tipo de mensagem de "acabou" aí fecha o loop
				if msgJSON["type"] == "ERROR":
					resend = True
				else:
					ans += [msgJSON]
				
				# TODO: esperar todo o stream de dados do servidor para um determinado pacote
				if msgJSON["type"] == "archives":
					localArchives = msgJSON["archives"]
					recv = True
					break
				if msgJSON["type"] == "END":
					recv = True
					break
				if msgJSON["type"] == "request":
					print(msgJSON["img"])
					recv = True
					break
				# TODO: verificar a ordem dos ACKs
				ackMessage = {
					"type": "ACK",
					"ord": ans[-2]["ord"],
					"ordn": ans[-1]["ord"],
					"value": "OK"
				}
				recvFirst = True
				clientSocket.sendto(bytes(json.dumps(ackMessage), encoding='latin-1'), dest)
				begin = millis_now()
				
			except:
				pass
			
		if millis_now() - time > TIMEOUT or not resend: # pacote perdido reenvia
			if not recvFirst:
				clientSocket.sendto(bytes(json.dumps(msg), encoding='latin-1'), dest)
				time = millis_now()
				resend = False
				
			else:
				# caso tenha dado timeout no server mas ja tenha começado o stream
				ackMessage = {
					"type": "ACK",
					"ord": ans[-2]["ord"],
					"ordn": ans[-1]["ord"],
					"value": "OK"
				}
				clientSocket.sendto(bytes(json.dumps(ackMessage), encoding='latin-1'), dest)
				time = millis_now()
				resend = False
	
	return recv, ans
	

def setup_connection():
	'''
	Configura dados de conexão socket udp
	'''
	clientSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	clientSocket.setblocking(False)
	
	serverIP = socket.gethostbyname("localhost")  # Endereco IP do Servidor
	serverPort = 5001
	dest = (serverIP, serverPort)
	
	return clientSocket, dest


## main
if __name__ == "__main__":
	lastCounter = -1
	localArchives = []

	clientSocket, dest = setup_connection()
	status, localArchives = connect_to_server(clientSocket, dest)
	print(status , localArchives)
	printMenu()
	
	while True:
		while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
			command = sys.stdin.readline()

			if command:
				if command == "1\n":
					printArchives(localArchives)
					
				elif command == "2\n":
					sendRequest(localArchives, dest)
					
				elif command == "3\n":
					clientSocket.close()
					print("\nClose socket")
					exit(0)
			else: 
				print('eof')
				exit(0)

			