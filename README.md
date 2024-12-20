# Guide d'exécution des playbooks Ansible

L'objectif de cette section est de présenter les étapes nécessaires pour exécuter les playbooks Ansible développés dans le cadre de ce projet. Le processus complet est structuré en trois étapes : déploiement des machines virtuelles, copie des laboratoires sur les machines virtuelles, et correction automatisée des laboratoires des étudiants.

## 1. Déploiement des machines virtuelles EVE-NG

Le playbook `deploy_rxi_vms.yml` effectue le déploiement des machines virtuelles EVE-NG. Cette étape initialise les VMs sur l'hyperviseur ESXi, géré via la plateforme vSphere, en utilisant un template prédéfini. Les paramètres réseau et les identifiants nécessaires sont également configurés.

### Pré-requis

Les variables de configuration se trouvent dans le fichier `variables.yml`. Les variables potentiellement à modifier sont :

- **Utilisateur système et EVE-NG**
  - `local_username` : utilisateur système et EVE-NG à créer pour l'étudiant.
  
- **Configuration des VMs**
  - `vm_base_name` : nom de base des VMs, suffixé par le dernier octet de l'adresse IP. Par exemple, avec `RXI_VM` et `starting_ip : 101`, la première VM sera nommée `RXI_VM_101`.
  - `vm_count` : nombre de VMs à déployer.
  - `vm_template` : template de base utilisé pour le déploiement. Le template doit exister sur vSphere.
  
- **Configuration réseau**
  - `ip_prefix` : préfixe des adresses IP utilisées par les VMs. Par exemple `10.190.139` pour le réseau `10.190.139.0/24`.
  - `starting_ip` : première adresse IP assignée. Par exemple, `101` pour `10.190.139.101`.
  - `gateway, subnet_mask, dns_servers` : paramètres réseau classiques à vérifier selon l'environnement cible.
  
- **Configuration vSphere**
  - `vm_datacenter, vm_folder, vm_datastore, network_name` : ces paramètres doivent correspondre aux ressources et réseaux configurés sur vSphere.

Le fichier `vars.yml` contient des informations sensibles telles que les identifiants pour vSphere et Vault. Pour des raisons de sécurité, il est préférable de chiffrer ce fichier avec Ansible Vault.

```yaml
vcenter_hostname: "<vcenter_hostname>"
vcenter_username: "<vcenter_username>"
vcenter_password: "<vcenter_password>"
vault_username: "<vault_username>"
vault_password: "<vault_password>"
vault_address: "<vault_address>"
```

```bash
ansible-vault encrypt vars.yml
```

Cette commande chiffre le fichier et oblige l'utilisateur à définir un mot de passe, lequel sera requis lors de chaque exécution de playbook nécessitant l'accès à ce fichier, à l'aide du flag `--ask-vault-pass`.

### Commande d'exécution

```bash
ansible-playbook playbooks/deploy_rxi_vms.yml --ask-vault-pass
```

**Résultat attendu** : Après l'exécution, les machines virtuelles seront disponibles sur vSphere dans le dossier `vm_folder`.

---

## 2. Copie des laboratoires sur les machines virtuelles

Le playbook `deploy_rxi_lab.yml` permet de copier les laboratoires EVE-NG sur les machines virtuelles déployées lors de la première étape, en s'appuyant sur les informations des machines virtuelles stockées dans Vault.

### Pré-requis

Le fichier `variables.yml` contient également les paramètres nécessaires pour la copie des laboratoires. Les variables à vérifier sont :

- **Chemin du fichier laboratoire**
  - `source_file` : spécifie le chemin vers le fichier `.unl` du laboratoire à copier.

- **Destination sur les machines virtuelles**
  - `destination_path` : indique l'emplacement cible sur les machines virtuelles (par défaut : `/opt/unetlab/labs/`).

### Accès aux machines virtuelles

Les informations des machines virtuelles, notamment leurs adresses IP, sont récupérées depuis Vault pour déterminer les cibles vers lesquelles le laboratoire doit être transféré. Les identifiants SSH utilisés pour la connexion aux machines virtuelles (`ssh_user` et `ssh_password`) sont définis dans `variables.yml`, qui correspondent aux identifiants root de la VM utilisée comme template.

### Commande d'exécution

```bash
ansible-playbook playbooks/deploy_rxi_lab.yml --ask-vault-pass
```

**Résultat attendu** : À la fin de l’exécution, le fichier de laboratoire spécifié dans `source_file` sera copié dans le répertoire défini par `destination_path` de chaque machine virtuelle. Les laboratoires pourront ensuite être ouverts et manipulés via l’interface web d’EVE-NG.

---

## 3. Correction automatisée des laboratoires

Le playbook `lab_correction.yml` est utilisé pour automatiser la correction des laboratoires EVE-NG en comparant les fichiers `.unl` des étudiants à une solution de référence. Il orchestre les scripts Python nécessaires pour parser les fichiers, extraire les configurations, et générer des rapports.

### Pré-requis

Le fichier `correction_vars.yml` contient les chemins nécessaires pour l'exécution des scripts de correction :

- **Dossier des fichiers `.unl` des étudiants**
  - `source_dir` : Chemin du répertoire contenant les fichiers `.unl` à corriger.

- **Fichiers intermédiaires et rapports**
  - `parsed_dir` : répertoire où les fichiers parsés seront générés.
  - `reports_dir` : répertoire où les rapports de correction seront sauvegardés.

- **Fichier de solution**
  - `solution_file` : fichier JSON contenant la solution de référence. Son nom doit correspondre à celui du fichier `.unl` ayant servi à générer la solution, avec l'extension remplacée par `.json`.
 
### Commande d'exécution

```bash
ansible-playbook playbooks/lab_correction.yml
```

**Résultat attendu** : Les laboratoires (fichiers `.unl` des étudiants) seront analysés et comparés à la solution définie (`solution_file`). Les rapports de correction montrant les différences seront exportés dans le répertoire `reports_dir` et disponibles aux formats texte et JSON.
