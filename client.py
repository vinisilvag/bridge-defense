#!/usr/bin/env python
import socket
import json
import sys

class BridgeDefense:
    def __init__(self, hostname, port1, gas):
        self._hostname = hostname
        self._port1 = port1
        self._gas = gas
        self._currentTurn = 0
        # rivers x bridges
        self._ships = [
            [[], [], [], [], [], [], [], []],
            [[], [], [], [], [], [], [], []],
            [[], [], [], [], [], [], [], []],
            [[], [], [], [], [], [], [], []],
        ]
        self._cannons = []
        self._finished = False

    def __del__(self):
        if not self._finished:
            self._gameTerminationRequest()

    def _get_ip_address(self):
        """
        Obtém endereço a partir de um hostname (escolhe preferencialmente IPv6).
        """
        try:
            # Obtém informações de endereço(s) para esse hostname (usando UDP)
            addr_info = socket.getaddrinfo(
                self._hostname, self._port1, socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP
            )

            # Itera sobre as informações
            for family, socktype, proto, canonname, sockaddr in addr_info:
                ip_address = sockaddr[0]
                # Escolhe endereço IPv6 se estiver disponível
                if family == socket.AF_INET6:
                    return (ip_address, family)
            # Se não houver IPv6, escolhe IPv4
            for family, socktype, proto, canonname, sockaddr in addr_info:
                ip_address = sockaddr[0]
                if family == socket.AF_INET:
                    return (ip_address, family)
        except socket.gaierror as e:
            print("Error:", e)
            sys.exit(0)

    def _serverCommunication(self, jsonRequest, serverNum, turnRequest=False):
        """
        Administra a comunicação com o servidor.

        Envia um JSON e recebe outro (se for mensagem de erro chama uma exceção e retorna None).

        Todos os métodos comunicantes com o servidor devem usá-lo.

        Obs.: O JSON informado deve estar no formato de string.
        """
        # Obtém endereço e família (IPv4 ou IPv6)
        ip_address, address_family = self._get_ip_address()

        while True:
            try:
                # Cria um socket UDP (e fecha a conexão automaticamente após as operações)
                with socket.socket(address_family, socket.SOCK_DGRAM) as client_socket:
                    # configura um timeout para não esperar indefinidamente
                    client_socket.settimeout(0.1)

                    # Transforma e envia a mensagem para o servidor (para a porta indicada nos parâmetros)
                    client_socket.sendto(
                        jsonRequest.encode(), (ip_address, self._port1 + serverNum)
                    )

                    if turnRequest:
                        responses = []

                        for _ in range(8):
                            response, _ = client_socket.recvfrom(2048)
                            response = response.decode()
                            dictResponse = json.loads(response)
                            if (
                                dictResponse["type"] == "gameover"
                                and dictResponse["status"] == 1
                            ):
                                print("JOGO ENCERRADO: " + dictResponse["description"])
                                self._finished = True
                                sys.exit(1)
                            elif (
                                dictResponse["type"] == "gameover"
                                and dictResponse["status"] == 0
                            ):
                                print("JOGO ENCERRADO SEM NENHUM ERRO.")
                                print(f"SCORE: {dictResponse['score']}")
                                self._gameTerminationRequest()
                                self._finished = True
                                sys.exit(0)
                            responses.append(dictResponse)

                        return responses
                    else:
                        # Recebe a resposta (com um tamanho máximo) e converte para JSON
                        response, _ = client_socket.recvfrom(2048)

                        # Decodifica os bits da resposta do servidor
                        response = response.decode()

                        # Verifica o tipo da mensagem para saber se é um game over ou não
                        dictResponse = json.loads(response)
                        if (
                            dictResponse["type"] == "gameover"
                            and dictResponse["status"] == 1
                        ):
                            print("JOGO ENCERRADO: " + dictResponse["description"])
                            self._finished = True
                        elif (
                            dictResponse["type"] == "gameover"
                            and dictResponse["status"] == 0
                        ):
                            print("JOGO ENCERRADO SEM NENHUM ERRO.")
                            print(f"SCORE: {dictResponse['score']}")
                            self._gameTerminationRequest()
                            self._finished = True
                            sys.exit(0)

                        # Se tudo ocorrer bem, retorna o JSON da resposta
                        return response

            except socket.timeout:
                print(
                    f"Ocorreu um timeout ao tentar conexão com o servidor {serverNum}. Tentando novamente..."
                )
            except socket.error as e:
                print("An error occurred. Retrying... Socket error:", e)

        # Se nenhum erro ocorrer, converte a resposta para JSON

    def _authenticationRequest(self):
        """
        Recebe um GAS, envia para o servidor, que retorna autenticação.
        """

        # Transforma os dados necessários para esse tipo de requisição em um JSON
        data = {"type": "authreq", "auth": self._gas}
        jsonMessage = json.dumps(data)

        # Faz a autenticação nos quatro servidores (rios)
        successfulAuthentication = True
        for i in range(0, 4):

            # Recebe a resposta do servidor e transforma em um dicionário
            jsonResponse = self._serverCommunication(jsonMessage, i)
            dictResponse = json.loads(jsonResponse)

            # Retorna o status da autenticação em cada servidor (rio)
            if dictResponse["status"] == 0:
                print(f"GAS autenticado no rio {i}")
                successfulAuthentication = successfulAuthentication < True
            else:
                print(f"Não foi possivel autenticar GAS no rio {i}")
                successfulAuthentication = successfulAuthentication < False
        # Retorna True somente se a autenticação for bem sucedida em todos os servidores
        return successfulAuthentication

    def _cannonPlacementRequest(self):
        data = {"type": "getcannons", "auth": self._gas}
        jsonMessage = json.dumps(data)

        # Todos os servidores respondem igualmente a requisição de canhões
        jsonResponse = self._serverCommunication(jsonMessage, 0)
        dictResponse = json.loads(jsonResponse)

        self._cannons = dictResponse["cannons"]

    def _turnStateRequest(self):
        data = {"type": "getturn", "auth": self._gas, "turn": self._currentTurn}
        jsonMessage = json.dumps(data)

        for i in range(4):
            responses = self._serverCommunication(jsonMessage, i, turnRequest=True)
            for bridge, response in enumerate(responses):
                ships = response["ships"]
                self._ships[i][bridge] = ships

                # Output dos turnos
                for ship in ships:
                   print(f"Navio {ship} no rio {i+1} ponte {bridge+1}.")

        self._currentTurn += 1

    def _shotMessage(self):
        """
            Atira nos melhores navios possíveis a partir das insformações
            das variáveis "__ships" e "__cannons", que representam o turno atual.
            A solução é especificada na documentação.
        """
        # ALGORITMO PARA DEFINIR EM QUE NAVIO OS CANHÕES DEVEM ATIRAR
        for cannon in self._cannons:
            # Adapta as posições de canhões às coerdenadas de navio
            coordinate_x = cannon[1]-1
            coordinate_y = cannon[0]-1  

            # Obtém todos os navios ao alcance e adiciona em uma lista, e armazena as suas coordenadas
            ships_lists = self._ships + [[None] * len(self._ships[0])]
            ships_in_range = []
            for i in range(2):
                if ships_lists[coordinate_x+i][coordinate_y] is not None:
                    ships = ships_lists[coordinate_x+i][coordinate_y]
                    for ship in ships:
                        ship['x_coordinate'] = coordinate_x+i
                        ship['y_coordinate'] = coordinate_y
                    ships_in_range.extend(ships)

            # Calcula quantos tiros cada navio ainda precisa para afundar
            hits_needed = {'frigate': 1, 'destroyer': 2, 'battleship': 3}
            chosen_ship = {}
            hits_to_sink_previous = 999
            for ship in ships_in_range:
                hull = ship['hull']
                hits = ship['hits']
                hits_to_sink = hits_needed[hull] - hits

                # Escolhe o navio que precisa de menos tiros para afundar
                if hits_to_sink < hits_to_sink_previous and hits < hits_needed[hull]:
                    chosen_ship = ship
                    hits_to_sink_previous = hits_to_sink
        
            # Envia ao servidor a mensagem para atirar no navio escolhido
            if chosen_ship.get('id') is not None:
                shot_json_message = {
                        "type": "shot",
                        "auth": gas,
                        "cannon": cannon,
                        "id": chosen_ship["id"]
                        }
                # Envia a mensagem
                shot_result = self._serverCommunication(json.dumps(shot_json_message), chosen_ship["x_coordinate"])
                shot_result = json.loads(shot_result)
                
                # Interpreta o resultado retornado pelo servidor
                if(shot_result.get("status") == 0):
                    
                    # Mensagem de sucesso
                    print(f"Canhão {shot_result.get('cannon')}" +
                            f" atirou no navio {shot_result.get('id')} com sucesso!")
                    
                    # Atualiza localmente a quantidade de tiros tomados por um navio
                    x = chosen_ship.get('x_coordinate')
                    y = chosen_ship.get('y_coordinate')
                    id = chosen_ship.get('id')
                    for s in range(len(self._ships[x][y])):
                        if id == shot_result.get('id') and id == self._ships[x][y][s].get('id'):
                            self._ships[x][y][s]['hits'] += 1
                        
                else:
                    # Informa o erro caso o tiro não tenha sido validado (mas o jogo continua normalmente)
                    print(f"Canhão {shot_result.get('cannon')}" +
                        " tentou atirar no navio {shot_result.get('id')}" +
                        " e não conseguiu: {shot_result.get('description')}")

    def _gameTerminationRequest(self):
        data = {"type": "quit", "auth": self._gas}
        jsonMessage = json.dumps(data)
        # Quit pode ser realizado em um servidor e todos encerrarão o jogo
        self._serverCommunication(jsonMessage, 0)

    def playGame(self):
        """
            Dá início ao jogo.
        """
        # ETAPA1: Faz a autenticação nos 4 rios
        print("--------- INICIANDO AUTENTICAÇÃO ---------")
        if not self._authenticationRequest():
            print(
                "Para continuar é preciso autenticar em todos os rios. Tente novamente."
            )
            sys.exit(0)

        # Armazena as posições dos canhões
        print("\n--------- RECEBENDO OS CANHÕES ---------")
        self._cannonPlacementRequest()
        print(f"Canhões: {self._cannons}")

        # Avança turno e atira nos navios a cada turno (até o fim do jogo)
        while True:
            print(f"\n--------- TURNO {self._currentTurn} ---------")
            self._turnStateRequest()

            # ETAPA4: Atira nos navios da melhor forma possível (a implementar)
            # desenvolver método "_shotMessage()"
            print("\n--------- ATIRANDO ---------")
            self._shotMessage()

            # Só pra facilitar no desenvolvimento
            #if self._currentTurn == 10:
            #    break

        # ETAPA6: Retorna score
        return None


if __name__ == "__main__":
    # verifica se o número de argumentos é três
    num_args = len(sys.argv)
    if num_args != 4:
        print(
            "Parâmetros incorretos. Como usar: python client.py <hostname> <port 1> <GAS>"
        )
        sys.exit(1)

    # Obtém os argumentos a partir dos parâmetros do programa na linha de comando
    host = sys.argv[1]
    port = int(sys.argv[2])
    gas = sys.argv[3]

    # EXEMPLO DE PARÂMETROS VALIDOS PARA TESTE
    # host = "pugna.snes.dcc.ufmg.br"
    # port = 51111
    # gas = "202011111122:1234567890:afc97aecb06dec27ded0534a4ceaf6aacb8c0291abd304ea708fc459ed0ac8eb+202011111123:1234567899:b7a40be27a38fd979186b0f7eeb45b706a2da859bba03f699d8cbf67b43d412e+0c2dc10ca2d44af785ddb45ad39c572c3754dcef38b1dc38b044a1ef002eece6"

    newGame = BridgeDefense(host, port, gas)
    newGame.playGame()
